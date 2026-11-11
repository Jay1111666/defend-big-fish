"""自由建造与战斗结算的回归检查。python -m unittest -v"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import unittest
import pygame
from config import PADS, COLS, ROWS, BLOCKED_CELLS, pad_at, PATH, TOWERS, FOOD_ENEMIES, DANGO_KINDS
from model import Game, Enemy, Tower, Obstacle, Projectile
from main import App
from progress import ProgressStore


def fire_tower(tower, dt, enemies, effects, obstacles=(), priority_target=None):
    """测试命中结果时，让本次发射的弹丸飞到目标。"""
    before = len(effects)
    tower.update(dt, enemies, effects, obstacles, priority_target)
    for effect in list(effects[before:]):
        if isinstance(effect, Projectile):
            effect.update(1, enemies, obstacles, effects)


class PlacementTests(unittest.TestCase):
    def test_preparation_freezes_attacks_and_resumes_at_next_wave(self):
        app = App(progress=ProgressStore(':memory:'))
        self.addCleanup(app.progress.close)
        self.addCleanup(pygame.quit)
        for kind in TOWERS:
            with self.subTest(tower=kind):
                app.reset(0)
                game = app.game
                game.coins = 1000
                pad = pad_at((416, 352))
                self.assertTrue(game.build(kind, pad))
                self.assertTrue(game.upgrade(game.towers[0]))
                game.sell(game.towers[0])
                self.assertTrue(game.build(kind, pad))
                tower = game.towers[0]
                obstacle = next(o for o in game.obstacles if o.position == (480, 352))
                game.select_target_at(obstacle.position)
                enemy = Enemy('shell', path=[(500, 352), (900, 352)])
                game.enemies = [enemy]
                position = enemy.position.copy()
                coins, hp = game.coins, obstacle.hp
                app.advance(3)
                self.assertEqual(enemy.position, position)
                self.assertEqual(enemy.hp, enemy.max_hp)
                self.assertEqual(obstacle.hp, hp)
                self.assertEqual(game.coins, coins)
                self.assertEqual(tower.cooldown, 0)
                self.assertFalse(game.effects)
                self.assertFalse(tower.beam_active)
                app.action('wave')
                app.advance(.6)
                self.assertNotEqual(enemy.position, position)
                if kind == 'moon':
                    self.assertEqual(enemy.slow_source, 'moon')
                else:
                    self.assertLess(obstacle.hp, hp)
                game.waves.queue.clear()
                for victim in game.enemies:
                    victim.take_damage(victim.hp)
                app.advance(1 / 60)
                self.assertFalse(game.waves.active)
                hp, cooldown = obstacle.hp, tower.cooldown
                effects = [(effect, effect.life) for effect in game.effects]
                tick = app.tick
                app.advance(3)
                self.assertEqual(obstacle.hp, hp)
                self.assertEqual(tower.cooldown, cooldown)
                self.assertEqual([(effect, effect.life) for effect in game.effects], effects)
                self.assertEqual(app.tick, tick)
                app.action('wave')
                app.advance(1.3)
                self.assertTrue(game.waves.active)
                if kind != 'moon':
                    self.assertLess(obstacle.hp, hp)

    def test_every_cell_and_failed_purchase(self):
        game = Game()
        self.assertEqual(game.towers, [])
        coins = game.coins
        for i, pos in enumerate(PADS):
            self.assertEqual(pad_at(pos), i)
            self.assertEqual(game.can_build(i), (i % COLS, i // COLS) not in BLOCKED_CELLS)
            if not game.can_build(i):
                self.assertFalse(game.build('bottle', i))
                self.assertEqual(game.coins, coins)
        self.assertFalse(game.build('bottle', -1))
        self.assertFalse(game.build('bottle', len(PADS)))
        self.assertFalse(game.build('bottle', None))
        pad = next(i for i in range(len(PADS)) if game.can_build(i))
        self.assertTrue(game.build('arrow', pad))
        self.assertFalse(game.build('bottle', pad))
        game.coins = 0
        self.assertFalse(game.build('bottle', pad + 1))

    def test_popup_then_purchase_and_pause(self):
        app = App(progress=ProgressStore(':memory:'))
        self.addCleanup(app.progress.close)
        def click(pos, button=1):
            app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=pos))
            app.draw()
        app.draw()
        click((416, 352))
        self.assertIsNotNone(app.build_pad)
        self.assertFalse(app.game.towers)
        for i in range(len(PADS)):
            if app.game.can_build(i):
                app.build_pad = i
                app.draw()
                self.assertTrue(pygame.Rect(0, 100, 1280, 620).contains(app.popup))
        app.build_pad = pad_at((416, 352))
        app.draw()
        app.action('pause')
        rect = next(rect for rect, action, _ in app.buttons if action == 'bottle')
        click(rect.center)
        self.assertTrue(app.paused)
        self.assertEqual(len(app.game.towers), 1)
        self.assertEqual(app.game.coins, 160)
        tower = app.selected
        app.action('upgrade')
        self.assertEqual(tower.level, 2)
        app.action('sell')
        self.assertEqual(app.game.coins, 188)
        self.assertFalse(app.game.towers)
        app.reset(0)
        app.draw()
        click((416, 352))
        click((416, 352), 3)
        self.assertIsNone(app.build_pad)
        app.action('wave')
        self.assertTrue(app.game.waves.active)
        app.action('restart')
        self.assertFalse(app.game.towers)
        self.assertEqual(app.game.coins, 230)
        pygame.quit()


class BattleTests(unittest.TestCase):
    def test_every_level_fifth_wave_spawns_only_its_own_dango(self):
        food = {kind for kind, _, _ in FOOD_ENEMIES}
        self.assertEqual(len(food), 16)
        for level, dango in enumerate(DANGO_KINDS):
            with self.subTest(level=level + 1):
                game = Game(level)
                ordinary = set()
                for index in range(len(game.config['waves'])):
                    self.assertTrue(game.waves.start())
                    spawned = []
                    game.waves.update(100, spawned)
                    kinds = [enemy.kind for enemy in spawned]
                    if index == 4:
                        self.assertEqual(kinds, [dango] * (14 + level))
                    else:
                        self.assertFalse(set(kinds) & set(DANGO_KINDS))
                        ordinary.update(set(kinds) - {'boss'})
                    game.waves.update(0, [])
                self.assertEqual(ordinary, food)

    def test_obstacles_leave_routes_clear_and_release_all_cells(self):
        for level, kind in ((0, 'balloon_basket'), (6, 'igloo'), (7, 'desert_well'),
                            (8, 'windmill'), (9, 'igloo')):
            with self.subTest(level=level + 1):
                game = Game(level)
                occupied = set()
                reserved = game.layout['path_cells'] | game.layout['home_cells']
                for obstacle in game.obstacles:
                    cells = {(pad % COLS, pad // COLS) for pad in obstacle.cells}
                    self.assertTrue(all(0 <= x < COLS and 0 <= y < ROWS for x, y in cells))
                    self.assertFalse(cells & (occupied | reserved))
                    self.assertTrue(all(not game.can_build(pad) for pad in obstacle.cells))
                    occupied.update(cells)
                obstacle = next(o for o in game.obstacles if o.kind == kind)
                for pad in obstacle.cells:
                    self.assertTrue(game.select_target_at(PADS[pad]))
                    self.assertIs(game.priority_target, obstacle)
                coins = game.coins
                obstacle.take_damage(obstacle.hp)
                game.update(0)
                self.assertIsNone(game.priority_target)
                self.assertEqual(game.coins, coins + obstacle.reward)
                self.assertTrue(all(game.can_build(pad) for pad in obstacle.cells))

    def test_last_three_levels_use_their_own_routes_and_reach_home(self):
        for level, theme, entry, home in (
            (7, 'desert', (3, 6), (15, 3)),
            (8, 'forest', (6, 1), (16, 6)),
            (9, 'ice', (15, 6), (8, 8)),
        ):
            with self.subTest(level=level + 1):
                game = Game(level)
                self.assertEqual(game.layout['theme'], theme)
                self.assertEqual(game.path[0], PADS[entry[1] * COLS + entry[0]])
                self.assertEqual(game.path[-1], PADS[home[1] * COLS + home[0]])
                for start, end in zip(game.path, game.path[1:]):
                    self.assertTrue(start[0] == end[0] or start[1] == end[1])
                game.waves.start()
                game.update(0)
                enemy = game.enemies[0]
                self.assertEqual(enemy.position, game.path[0])
                enemy.update(100)
                self.assertEqual(enemy.status, 'escaped')
                self.assertEqual(enemy.position, game.path[-1])

    def test_path_slow_and_single_settlement(self):
        enemy = Enemy('crab')
        enemy.update(100)
        self.assertEqual(enemy.status, 'escaped')
        self.assertEqual(enemy.position, PATH[-1])
        enemy = Enemy('crab')
        enemy.apply_slow(.5, 1)
        enemy.update(2)
        self.assertAlmostEqual(enemy.progress, 84)
        game = Game()
        enemy.take_damage(1000)
        game.enemies.append(enemy)
        game.update(.01)
        coins = game.coins
        game.update(.01)
        self.assertEqual(game.coins, coins)

    def test_no_defense_loses(self):
        game = Game()
        for _ in range(60000):
            if not game.waves.active:
                game.waves.start()
            game.update(1 / 60)
            if game.state != 'playing':
                break
        self.assertEqual(game.state, 'lost')


class TargetingTests(unittest.TestCase):
    def test_overlapping_enemies_only_select_one_and_never_transfer_lock(self):
        game = Game()
        lower, upper = Enemy('crab'), Enemy('crab')
        lower.position.update(288, 352)
        upper.position.update(lower.position)
        game.enemies = [lower, upper]
        self.assertTrue(game.select_target_at(upper.position))
        self.assertIs(game.priority_target, upper)
        upper.take_damage(1000)
        game.update(0)
        self.assertIsNone(game.priority_target)
        self.assertEqual(lower.hp, lower.max_hp)
        self.assertEqual(game.enemies, [lower])
        game.select_target_at(lower.position)
        lower.status = 'escaped'
        game.update(0)
        self.assertIsNone(game.priority_target)
        self.assertEqual(game.lives, 9)

    def test_obstacle_reward_once_release_cell_and_restore_on_restart(self):
        game = Game()
        obstacle = game.obstacles[0]
        self.assertTrue(game.select_target_at(obstacle.position))
        self.assertIs(game.priority_target, obstacle)
        self.assertFalse(game.can_build(obstacle.pad))
        coins = game.coins
        obstacle.take_damage(10000)
        game.update(0)
        self.assertEqual(game.coins, coins + obstacle.reward)
        self.assertIsNone(game.priority_target)
        self.assertNotIn(obstacle, game.obstacles)
        game.update(0)
        self.assertEqual(game.coins, coins + obstacle.reward)
        self.assertTrue(game.build('star', obstacle.pad))
        self.assertFalse(Game().can_build(obstacle.pad))

    def test_priority_in_range_and_fallback_out_of_range(self):
        tower = Tower('bottle', pad_at((416, 352)))
        near, advanced = Enemy('crab'), Enemy('crab')
        near.position.update(470, 352)
        advanced.position.update(450, 352)
        advanced.progress = 100
        fire_tower(tower, 0, [near, advanced], [], priority_target=near)
        self.assertEqual(near.hp, 43)
        self.assertEqual(advanced.hp, 65)
        near.position.update(1000, 352)
        tower.cooldown = 0
        fire_tower(tower, 0, [near, advanced], [], priority_target=near)
        self.assertEqual(advanced.hp, 43)

    def test_inflight_shots_do_not_transfer_dead_obstacle_lock(self):
        game = Game()
        self.assertTrue(game.build('bottle', pad_at((416, 352))))
        self.assertTrue(game.build('bottle', pad_at((544, 352))))
        obstacle = next(o for o in game.obstacles if o.position == (480, 352))
        game.select_target_at(obstacle.position)
        obstacle.hp = 1
        enemy = Enemy('crab')
        enemy.position.update(obstacle.position)
        game.enemies = [enemy]
        game.waves.active = True
        coins = game.coins
        game.update(0)
        self.assertEqual(obstacle.hp, 1)
        for shot in list(game.effects):
            shot.update(1, game.enemies, game.obstacles, game.effects)
        game.update(0)
        self.assertEqual(game.coins, coins + obstacle.reward)
        self.assertEqual(enemy.hp, enemy.max_hp)
        self.assertIsNone(game.priority_target)
        for tower in game.towers:
            tower.cooldown = 0
        game.update(0)
        self.assertTrue(all(shot.target is enemy for shot in game.effects
                            if isinstance(shot, Projectile)))

    def test_star_splash_center_radius_and_single_direct_hit(self):
        for main_kind in ['enemy', 'obstacle']:
            with self.subTest(main_kind=main_kind):
                tower = Tower('star', pad_at((416, 352)))
                primary = Enemy('crab') if main_kind == 'enemy' else Obstacle('trees', 0)
                primary.position.update(556, 352)
                overlapping = Enemy('crab')
                overlapping.position.update(primary.position)
                boundary = Enemy('crab')
                boundary.position.update(632, 352)
                outside = Enemy('crab')
                outside.position.update(632.1, 352)
                beside_tower = Enemy('crab')
                beside_tower.position.update(tower.position)
                nearby_obstacle = Obstacle('crystal', 0)
                nearby_obstacle.position.update(610, 352)
                enemies = [overlapping, boundary, outside, beside_tower]
                obstacles = [nearby_obstacle]
                if main_kind == 'enemy':
                    enemies.append(primary)
                else:
                    obstacles.append(primary)
                effects = []
                fire_tower(tower, 0, enemies, effects, obstacles, primary)
                self.assertEqual(primary.hp, primary.max_hp - 30)
                self.assertEqual(overlapping.hp, 65 - 12)
                self.assertEqual(boundary.hp, 65 - 12)
                self.assertEqual(outside.hp, 65)
                self.assertEqual(beside_tower.hp, 65)
                self.assertEqual(nearby_obstacle.hp, nearby_obstacle.max_hp - 12)
                self.assertEqual(effects[0].end, tuple(primary.position))
                # 主目标被直击击杀，仍以这次命中位置产生溅射。
                primary.hp = 1
                tower.cooldown = 0
                fire_tower(tower, 0, enemies, effects, obstacles, primary)
                self.assertEqual(primary.status, 'dead')
                self.assertEqual(boundary.hp, 65 - 24)
                self.assertEqual(effects[-1].end, (556, 352))

    def test_arrow_can_clear_obstacles_and_moon_keeps_slowing(self):
        enemy = Enemy('crab')
        enemy.position.update(480, 352)
        obstacle = Obstacle('trees', 0)
        obstacle.position.update(480, 352)
        tower = Tower('arrow', pad_at((416, 352)))
        fire_tower(tower, 0, [enemy], [], [obstacle], obstacle)
        self.assertEqual(enemy.hp, 47)
        self.assertEqual(obstacle.hp, 122)
        moon = Tower('moon', tower.pad)
        fire_tower(moon, 0, [enemy], [], [obstacle], obstacle)
        self.assertEqual(obstacle.hp, 122)
        self.assertEqual(enemy.slow_source, 'moon')
        self.assertEqual(enemy.active_slow.multiplier, .58)
        self.assertEqual(enemy.active_slow.remaining, .8)

    def test_obstacles_do_not_block_wave_completion(self):
        game = Game()
        game.waves.index = len(game.config['waves']) - 1
        game.waves.active = True
        game.update(0)
        self.assertTrue(game.obstacles)
        self.assertEqual(game.state, 'won')

    def test_mouse_select_cancel_and_build_star(self):
        app = App(progress=ProgressStore(':memory:'))
        self.addCleanup(app.progress.close)
        def click(position, button=1):
            app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=position))
            app.draw()
        app.draw()
        obstacle = next(o for o in app.game.obstacles if o.position == (480, 352))
        click(obstacle.position)
        self.assertIs(app.game.priority_target, obstacle)
        self.assertIsNone(app.build_pad)
        click(obstacle.position, 3)
        self.assertIsNone(app.game.priority_target)
        click((416, 352))
        star_button = next(rect for rect, action, _ in app.buttons if action == 'star')
        click(star_button.center)
        self.assertEqual(app.game.towers[0].kind, 'star')
        self.assertEqual(app.game.coins, 100)
        click((416, 352), 3)
        lower, upper = Enemy('crab'), Enemy('crab')
        lower.position.update(288, 352)
        upper.position.update(lower.position)
        app.game.enemies = [lower, upper]
        click(upper.position)
        self.assertIs(app.game.priority_target, upper)
        app.reset(0)
        self.assertIsNone(app.game.priority_target)
        self.assertFalse(app.game.towers)
        pygame.quit()


if __name__ == '__main__':
    unittest.main()
