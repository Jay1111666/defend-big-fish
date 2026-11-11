"""战斗逻辑与渲染分离，支持无窗口模拟。"""
from dataclasses import dataclass
import pygame
from config import PATH, PADS, COLS, TILE, OBSTACLE_STATS, TOWERS, ENEMIES, level_config


class AttackTarget:
    def __init__(self, position, hp, reward):
        self.position = pygame.Vector2(position)
        self.hp = self.max_hp = hp
        self.reward = reward
        self.status = 'alive'

    def take_damage(self, amount):
        if self.status == 'alive':
            self.hp = max(0, self.hp - amount)
            if self.hp == 0:
                self.status = 'dead'


class Obstacle(AttackTarget):
    def __init__(self, kind, pad, width=1, height=1):
        spec = OBSTACLE_STATS[kind]
        x, y = PADS[pad]
        super().__init__((x + (width - 1) * TILE / 2, y + (height - 1) * TILE / 2),
                         spec['hp'], spec['reward'])
        self.kind = kind
        self.pad = pad
        self.name = spec['name']
        self.width, self.height = width, height
        self.cells = {pad + row * COLS + col for row in range(height) for col in range(width)}

    @property
    def bounds(self):
        return pygame.Rect(self.position.x - self.width * TILE / 2,
                           self.position.y - self.height * TILE / 2,
                           self.width * TILE, self.height * TILE)


def in_range(origin, target, radius):
    if isinstance(target, Obstacle):
        bounds = target.bounds
        nearest = (max(bounds.left, min(bounds.right, origin[0])),
                   max(bounds.top, min(bounds.bottom, origin[1])))
        return pygame.Vector2(origin).distance_squared_to(nearest) <= radius ** 2
    return pygame.Vector2(origin).distance_squared_to(target.position) <= radius ** 2


@dataclass
class SlowEffect:
    source: str
    multiplier: float
    remaining: float


class Enemy(AttackTarget):
    def __init__(self, kind, hp_scale=1, path=None):
        spec = ENEMIES[kind]
        self.path = PATH if path is None else path
        super().__init__(self.path[0], spec['hp'] * hp_scale, spec['reward'])
        self.kind = kind
        self.speed = spec['speed']
        self.name = spec.get('name', '怪兽')
        self.hit_radius = spec.get('hit_radius', 24)
        self.leak_damage = spec.get('leak_damage', 1)
        self.next_waypoint = 1
        self.progress = 0.0
        self.slows = []

    @property
    def active_slow(self):
        # 两类效果独立计时，但只取月亮（优先）或风扇中的一个倍率。
        moons = [effect for effect in self.slows if effect.source == 'moon']
        return min(moons or self.slows, key=lambda effect: effect.multiplier, default=None)

    @property
    def slow_source(self):
        effect = self.active_slow
        return effect.source if effect else None

    def apply_slow(self, multiplier, duration, source='moon'):
        if duration <= 0:
            return
        for effect in self.slows:
            if effect.source == source and effect.multiplier == multiplier:
                effect.remaining = max(effect.remaining, duration)
                return
        self.slows.append(SlowEffect(source, multiplier, duration))

    def update(self, dt):
        if self.status != 'alive':
            return
        # 在减速到期时切分时间，避免帧长改变移动距离。
        remaining = dt
        while remaining > 1e-9 and self.status == 'alive':
            deadlines = [effect.remaining for effect in self.slows]
            step = min([remaining, *deadlines])
            active = self.active_slow
            factor = active.multiplier if active else 1.0
            self._move(self.speed * factor * step)
            for effect in self.slows:
                effect.remaining -= step
            self.slows = [effect for effect in self.slows if effect.remaining > 1e-9]
            remaining -= step

    def _move(self, distance):
        while distance > 0 and self.next_waypoint < len(self.path):
            offset = pygame.Vector2(self.path[self.next_waypoint]) - self.position
            length = offset.length()
            travel = min(distance, length)
            if length:
                self.position += offset * (travel / length)
            self.progress += travel
            distance -= travel
            if travel >= length:
                self.next_waypoint += 1
            else:
                break
        if self.next_waypoint == len(self.path):
            self.status = 'escaped'


@dataclass
class Effect:
    kind: str
    start: tuple
    end: tuple
    radius: float = 0
    life: float = .23

    def update(self, dt, enemies, obstacles, effects):
        self.life -= dt


class Projectile:
    """弹丸跟随原实例飞行；死亡不换目标，星星在最后命中点爆炸。"""
    def __init__(self, kind, start, target, damage, radius=0, splash_damage=0):
        self.kind = kind
        self.start = tuple(start)
        self.position = pygame.Vector2(start)
        self.end = tuple(target.position)
        self.target = target
        self.damage = damage
        self.radius = radius
        self.splash_damage = splash_damage
        self.life = 3.0
        self.speed = 460 if kind == 'bottle' else 360

    def update(self, dt, enemies, obstacles, effects):
        if self.life <= 0:
            return
        self.life -= dt
        if self.target.status == 'escaped':
            self.life = 0
            return
        if self.target.status == 'alive':
            self.end = tuple(self.target.position)
        delta = pygame.Vector2(self.end) - self.position
        distance = delta.length()
        if distance > self.speed * dt:
            if distance:
                self.position += delta * (self.speed * dt / distance)
            return
        self.position.update(self.end)
        self.life = 0
        self.target.take_damage(self.damage)
        if self.kind == 'star':
            for victim in [*enemies, *obstacles]:
                if victim is not self.target and victim.status == 'alive' and in_range(self.end, victim, self.radius):
                    victim.take_damage(self.splash_damage)
            effects.append(Effect('star_hit', self.end, self.end, self.radius, .30))
        else:
            effects.append(Effect('bean_hit', self.end, self.end, 12, .16))


class PiercingProjectile:
    """固定方向的穿透弹，用整段轨迹检测高速碰撞。"""
    def __init__(self, kind, start, target_position, damage, distance, speed, slow=None):
        self.kind = kind
        self.position = pygame.Vector2(start)
        direction = pygame.Vector2(target_position) - self.position
        self.direction = direction.normalize() if direction.length_squared() else pygame.Vector2(1, 0)
        self.damage = damage
        self.slow = slow
        self.remaining_distance = distance
        self.speed = speed
        self.life = distance / speed
        self.hit_targets = set()

    def update(self, dt, enemies, obstacles, effects):
        if self.life <= 0 or dt <= 0:
            return
        start = self.position.copy()
        travel = min(self.remaining_distance, self.speed * dt)
        end = start + self.direction * travel
        for victim in [*enemies, *obstacles]:
            if victim.status != 'alive' or victim in self.hit_targets:
                continue
            if isinstance(victim, Obstacle):
                bounds = victim.bounds.inflate(20, 20)
                hit = bool(bounds.clipline(start, end)) or bounds.collidepoint(start)
            else:
                along = max(0, min(travel, (victim.position - start).dot(self.direction)))
                nearest = start + self.direction * along
                hit = victim.position.distance_squared_to(nearest) <= (victim.hit_radius + 10) ** 2
            if hit:
                self.hit_targets.add(victim)
                victim.take_damage(self.damage)
                if self.slow and isinstance(victim, Enemy) and victim.status == 'alive':
                    multiplier, duration = self.slow
                    victim.apply_slow(multiplier, duration, self.kind)
        self.position = end
        self.remaining_distance -= travel
        self.life = max(0, self.remaining_distance / self.speed)


class Tower:
    AIMED_KINDS = ('arrow', 'bottle', 'rocket')
    RECOIL_TIME = .14

    def __init__(self, kind, pad):
        self.kind = kind
        self.pad = pad
        self.position = pygame.Vector2(PADS[pad])
        self.level = 1
        self.cooldown = 0
        self.spent = TOWERS[kind]['cost']
        self.beam_target = None
        self.aim_angle = -45
        self.recoil = 0

    @property
    def radius(self):
        spec = TOWERS[self.kind]
        return spec['radius'] + (self.level - 1) * spec.get('radius_step', 12)

    @property
    def upgrade_cost(self):
        return round(TOWERS[self.kind]['cost'] * (.7 + self.level * .3))

    def update(self, dt, enemies, effects, obstacles=(), priority_target=None):
        if self.kind == 'magic':
            self.update_beam(dt, enemies, obstacles, priority_target)
            return
        self.cooldown = max(0, self.cooldown - dt)
        aimed = self.kind in self.AIMED_KINDS
        self.recoil = max(0, self.recoil - dt)
        if self.cooldown > 0 and not aimed:
            return
        targets = [e for e in enemies if e.status == 'alive'
                   and in_range(self.position, e, self.radius)]
        spec = TOWERS[self.kind]
        # 月亮保留范围减速行为。伤害塔优先攻击射程内的标记对象。
        target = max(targets, key=lambda e: e.progress, default=None)
        if (self.kind != 'moon' and priority_target is not None
                and priority_target.status == 'alive'
                and in_range(self.position, priority_target, self.radius)):
            target = priority_target
        if self.kind == 'sun' and target is None:
            target = next((o for o in obstacles if o.status == 'alive'
                           and in_range(self.position, o, self.radius)), None)
        if target is None:
            return
        launch_point = self.position
        if aimed:
            offset = target.position - self.position
            if offset.length_squared():
                distance, angle = offset.as_polar()
                turn = (angle - self.aim_angle + 180) % 360 - 180
                step = 900 * dt
                self.aim_angle += max(-step, min(step, turn)) if self.cooldown > 0 else turn
                launch_point = self.position + offset * (min(21, distance / 2) / distance)
        if self.cooldown > 0:
            return
        if aimed:
            self.recoil = self.RECOIL_TIME
        damage = spec['damage'] * (1 + .65 * (self.level - 1))
        self.cooldown = spec['interval'] / (1 + .1 * (self.level - 1))
        if self.kind == 'moon':
            for enemy in targets:
                enemy.apply_slow(spec['slow_factor'] - .08 * (self.level - 1), spec['slow_duration'], 'moon')
            effects.append(Effect('moon', tuple(self.position), tuple(self.position), self.radius, .55))
        elif self.kind in ('fan', 'rocket'):
            slow = None
            if self.kind == 'fan':
                slow = spec['slow_factor'] - .05 * (self.level - 1), spec['slow_duration']
            travel = spec['flight_distance'] + 25 * (self.level - 1) - launch_point.distance_to(self.position)
            effects.append(PiercingProjectile(self.kind, launch_point, target.position, damage,
                                              travel, spec['projectile_speed'], slow))
        elif self.kind == 'sun':
            for victim in [*enemies, *obstacles]:
                if victim.status == 'alive' and in_range(self.position, victim, self.radius):
                    victim.take_damage(damage)
            effects.append(Effect('sun', tuple(self.position), tuple(self.position), self.radius, .55))
        elif self.kind in ('bottle', 'star'):
            effects.append(Projectile(self.kind, launch_point, target, damage,
                                      spec.get('splash_radius', 0) + 8 * (self.level - 1),
                                      spec.get('splash_damage', 0) * (1 + .65 * (self.level - 1))))
        elif self.kind == 'arrow':
            center = target.position.copy()
            blast = 64 + 8 * (self.level - 1)
            for victim in [*enemies, *obstacles]:
                if victim.status == 'alive' and in_range(center, victim, blast):
                    victim.take_damage(damage)
            effects.append(Effect(self.kind, tuple(launch_point), tuple(center), blast, .39))

    @property
    def beam_active(self):
        return (self.beam_target is not None and self.beam_target.status == 'alive'
                and in_range(self.position, self.beam_target, self.radius))

    def update_beam(self, dt, enemies, obstacles, priority_target):
        live_targets = [*enemies, *obstacles]
        if not self.beam_active or self.beam_target not in live_targets:
            self.beam_target = None
        if (priority_target in live_targets and priority_target is not None
                and priority_target.status == 'alive' and in_range(self.position, priority_target, self.radius)):
            self.beam_target = priority_target
        elif self.beam_target is None:
            self.beam_target = max((e for e in enemies if e.status == 'alive'
                                    and in_range(self.position, e, self.radius)),
                                   key=lambda e: e.progress, default=None)
        if self.beam_target is not None:
            # damage 为每秒伤害；没有周期性冷却或激光闪断。
            self.beam_target.take_damage(TOWERS['magic']['damage'] * (1 + .65 * (self.level - 1)) * dt)
            if self.beam_target.status != 'alive':
                self.beam_target = None


class WaveManager:
    def __init__(self, config):
        self.config = config
        self.index = -1
        self.queue = []
        self.timer = 0
        self.active = False
        layout = config['layout']
        self.routes = layout.get('routes', (layout['path'],))
        self.next_route = 0

    def start(self):
        if self.active or self.index + 1 >= len(self.config['waves']):
            return False
        self.index += 1
        self.queue = list(self.config['waves'][self.index]['enemies'])
        self.timer = 0
        self.active = True
        return True

    def update(self, dt, enemies):
        if not self.active:
            return
        self.timer -= dt
        while self.queue and self.timer <= 0:
            enemies.append(Enemy(self.queue.pop(0), self.config['hp_scale'], self.routes[self.next_route]))
            self.next_route = (self.next_route + 1) % len(self.routes)
            self.timer += self.config['waves'][self.index]['interval']
        if not self.queue and not enemies:
            self.active = False


class Game:
    def __init__(self, level=0):
        self.level = level
        self.config = level_config(level)
        self.layout = self.config['layout']
        self.path = self.layout['path']
        self.coins = self.config['coins']
        self.lives = self.config['lives']
        self.enemies = []
        self.obstacles = [Obstacle(kind, row * COLS + col, width, height)
                          for kind, col, row, width, height in self.layout['obstacles']]
        self.priority_target = None
        self.towers = []
        self.effects = []
        self.waves = WaveManager(self.config)
        self.state = 'playing'
        self.kills = 0
        self.boss_announced = False
        self.boss_intro = 0

    @property
    def boss(self):
        return next((enemy for enemy in self.enemies
                     if enemy.kind == 'boss' and enemy.status == 'alive'), None)

    def can_build(self, pad):
        if type(pad) is not int or not 0 <= pad < len(PADS):
            return False
        cell = (pad % COLS, pad // COLS)
        land = self.layout.get('land_cells')
        return ((land is None or cell in land)
                and cell not in self.layout['path_cells'] | self.layout['home_cells']
                and not any(pad in o.cells and o.status == 'alive' for o in self.obstacles)
                and not any(t.pad == pad for t in self.towers))

    def select_target_at(self, position):
        if self.state != 'playing':
            return False
        # 后绘制的怪兽在视觉最上层，重叠时仅选这个实例，不按坐标批量标记。
        for enemy in reversed(self.enemies):
            if enemy.status == 'alive' and enemy.position.distance_squared_to(position) <= enemy.hit_radius ** 2:
                self.priority_target = enemy
                return True
        for obstacle in reversed(self.obstacles):
            if obstacle.status == 'alive' and obstacle.bounds.inflate(0, 12).collidepoint(position):
                self.priority_target = obstacle
                return True
        return False

    def build(self, kind, pad):
        if (self.state != 'playing' or not isinstance(kind, str)
                or kind not in TOWERS or not self.can_build(pad)
                or self.coins < TOWERS[kind]['cost']):
            return False
        self.coins -= TOWERS[kind]['cost']
        self.towers.append(Tower(kind, pad))
        return True

    def upgrade(self, tower):
        if self.state != 'playing' or tower not in self.towers or tower.level >= 3 or self.coins < tower.upgrade_cost:
            return False
        cost = tower.upgrade_cost
        self.coins -= cost
        tower.spent += cost
        tower.level += 1
        return True

    def sell(self, tower):
        if self.state == 'playing' and tower in self.towers:
            self.coins += int(tower.spent * .7)
            self.towers.remove(tower)

    def update(self, dt):
        if self.state != 'playing':
            return 0
        self.waves.update(dt, self.enemies)
        if self.waves.active:
            self.boss_intro = max(0, self.boss_intro - dt)
            if self.boss is not None and not self.boss_announced:
                self.boss_announced = True
                self.boss_intro = 4
            for enemy in self.enemies:
                enemy.update(dt)
            for tower in self.towers:
                tower.update(dt, self.enemies, self.effects, self.obstacles, self.priority_target)
            # 拷贝列表，命中特效从下一帧开始计时，避免同一帧被更新两次。
            for effect in list(self.effects):
                effect.update(dt, self.enemies, self.obstacles, self.effects)
            self.effects = [effect for effect in self.effects if effect.life > 0]
        hits = 0
        for enemy in self.enemies:
            if enemy.status == 'dead':
                self.coins += enemy.reward
                self.kills += 1
            elif enemy.status == 'escaped':
                lives_left = max(0, self.lives - enemy.leak_damage)
                hits += int(lives_left < self.lives)
                self.lives = lives_left
        self.enemies = [e for e in self.enemies if e.status == 'alive']
        for obstacle in self.obstacles:
            if obstacle.status == 'dead':
                self.coins += obstacle.reward
        self.obstacles = [o for o in self.obstacles if o.status == 'alive']
        if (self.priority_target is not None
                and (self.priority_target.status != 'alive'
                     or self.priority_target not in [*self.enemies, *self.obstacles])):
            self.priority_target = None
        if self.waves.active and not self.waves.queue and not self.enemies:
            self.waves.active = False
        if self.lives == 0:
            self.state = 'lost'
        elif self.waves.index == len(self.config['waves']) - 1 and not self.waves.active:
            self.state = 'won'
        return hits
