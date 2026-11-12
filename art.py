"""云端花园绘制与打包后的素材定位。"""
import math
import random
import sys
from pathlib import Path
import pygame
from config import (WIDTH, HEIGHT, TILE, GRID_X, GRID_Y, BAY_SHORE, CHARACTERS,
                    FOOD_ENEMIES, FOOD_GROUPS, DANGO_KINDS, map_config)

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
WHITE = (255, 250, 242)
INK = (54, 42, 81)
MUTED = (129, 113, 151)
PLUM = (73, 54, 106)
TEAL = (56, 154, 158)
FONTS = {}


def text(surface, value, pos, size=20, color=INK, center=False, bold=False):
    key = size, bold
    if key not in FONTS:
        bundled = ROOT / 'assets' / 'fonts' / 'game-cjk.otf'
        path = str(bundled) if bundled.exists() else pygame.font.match_font('microsoftyahei,simhei,notosanscjk,arial', bold=bold)
        FONTS[key] = pygame.font.Font(path, size)
        if bundled.exists():
            FONTS[key].set_bold(bold)
    rendered = FONTS[key].render(str(value), True, color)
    rect = rendered.get_rect(center=pos) if center else rendered.get_rect(topleft=pos)
    surface.blit(rendered, rect)


def panel(surface, rect, color=WHITE, border=None, radius=18):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, rect, 2, border_radius=radius)


def star(surface, center, radius, color, rotation=-math.pi / 2):
    points = []
    for i in range(10):
        angle = rotation + i * math.pi / 5
        length = radius if i % 2 == 0 else radius * .46
        points.append((center[0] + math.cos(angle) * length, center[1] + math.sin(angle) * length))
    pygame.draw.polygon(surface, color, points)


class Art:
    def __init__(self):
        # Pygame 重新初始化后必须重新创建字体，避免复用已释放的 SDL 资源。
        FONTS.clear()
        self.images = {}
        self.scaled = {}
        atlas = pygame.image.load(str(ROOT / 'assets' / 'sprites.png')).convert_alpha()
        keys = ['bottle', 'moon', 'arrow', 'trees', 'crystal', 'chest']
        for i, key in enumerate(keys):
            left = round(i % 3 * atlas.get_width() / 3)
            right = round((i % 3 + 1) * atlas.get_width() / 3)
            top = round(i // 3 * atlas.get_height() / 2)
            bottom = round((i // 3 + 1) * atlas.get_height() / 2)
            sprite = atlas.subsurface((left, top, right - left, bottom - top)).copy()
            self.images[key] = sprite.subsurface(sprite.get_bounding_rect(min_alpha=12)).copy()
        for key, character in CHARACTERS.items():
            sprite = pygame.image.load(str(ROOT / 'assets' / character['asset'])).convert_alpha()
            self.images[key] = sprite.subsurface(sprite.get_bounding_rect(min_alpha=12)).copy()
            sheet = pygame.image.load(str(ROOT / 'assets' / f'{key}-reactions.png')).convert_alpha()
            half = sheet.get_width() // 2
            for i, threshold in enumerate((7, 3)):
                pose = sheet.subsurface((i * half, 0, half, sheet.get_height()))
                self.images[f'{key}-{threshold}'] = pose.subsurface(pose.get_bounding_rect(min_alpha=12)).copy()
        currency = pygame.image.load(str(ROOT / 'assets' / 'star-currency.png')).convert_alpha()
        self.images['currency'] = currency.subsurface(currency.get_bounding_rect(min_alpha=12)).copy()
        star_tower = pygame.image.load(str(ROOT / 'assets' / 'star-tower.png')).convert_alpha()
        self.images['star'] = star_tower.subsurface(star_tower.get_bounding_rect(min_alpha=12)).copy()
        boss = pygame.image.load(str(ROOT / 'assets' / 'controller-boss.png')).convert_alpha()
        self.images['boss'] = boss.subsurface(boss.get_bounding_rect(min_alpha=12)).copy()
        ice_atlas = pygame.image.load(str(ROOT / 'assets' / 'ice-sprites.png')).convert_alpha()
        for i, key in enumerate(['sun', 'magic', 'igloo', 'iceberg', 'icecrystal', 'snowtrees']):
            left, right = round(i % 3 * ice_atlas.get_width() / 3), round((i % 3 + 1) * ice_atlas.get_width() / 3)
            top, bottom = round(i // 3 * ice_atlas.get_height() / 2), round((i // 3 + 1) * ice_atlas.get_height() / 2)
            # 图集冰屋/雪松的外沿略跨等分线，按两件素材之间的透明空隙切分。
            split = round(ice_atlas.get_width() * (992 if i < 3 else 1000) / 1536)
            if i % 3 == 1:
                right = split
            elif i % 3 == 2:
                left = split
            sprite = ice_atlas.subsurface((left, top, right - left, bottom - top)).copy()
            self.images[key] = sprite.subsurface(sprite.get_bounding_rect(min_alpha=12)).copy()
        self.background = pygame.transform.smoothscale(
            pygame.image.load(str(ROOT / 'assets' / 'cloud-garden.png')).convert(), (WIDTH, HEIGHT))
        self.ice_background = pygame.transform.smoothscale(
            pygame.image.load(str(ROOT / 'assets' / 'ice-garden.png')).convert(), (WIDTH, HEIGHT))
        for filename, columns, rows, keys in (
            ('forest-sprites.png', 3, 2, ('fan', 'moon', 'stump', 'rocks', 'forest', 'windmill')),
            ('bay-sprites.png', 3, 2, ('fan-flight', 'rocket-flight', 'rocket', 'lighthouse', 'rowboat', 'driftwood')),
            ('strait-props.png', 2, 2, ('lifebuoy', 'message_bottle', 'ice_pop', 'rubber_duck')),
            ('turret-heads.png', 2, 2, ('arrow-head', 'bottle-head', 'rocket-head', 'turret-base')),
            ('moss-props.png', 2, 2, ('acorn', 'moss_rock', 'rope_fence', 'spring_pool')),
            ('food-monsters.png', 4, 4, tuple(kind for kind, _, _ in FOOD_ENEMIES)),
            ('dango-monsters-a.png', 2, 2, DANGO_KINDS[:4]),
            ('dango-monsters-b.png', 2, 2, DANGO_KINDS[4:8]),
            ('dango-monsters-c.png', 2, 2, DANGO_KINDS[8:]),
            ('cloud-snow-props.png', 3, 3, ('balloon_basket', 'rainbow_cloud', 'orange_planet',
                                           'gold_planet', 'cupcake', 'winter_hat',
                                           'coin_pouch', 'snow_logs', 'cloud_trees')),
            ('desert-props.png', 2, 2, ('green_cactus', 'orange_cactus', 'tall_cactus', 'sandstone')),
            ('final-maps-props.png', 3, 2, ('ram_skull', 'desert_well', 'pine',
                                           'snow_bush', 'pink_pop', 'sandstone_small')),
        ):
            atlas = pygame.image.load(str(ROOT / 'assets' / filename)).convert_alpha()
            width, height = atlas.get_size()
            for i, key in enumerate(keys):
                col, row = i % columns, i // columns
                left, right = round(col * width / columns), round((col + 1) * width / columns)
                top, bottom = round(row * height / rows), round((row + 1) * height / rows)
                if filename == 'strait-props.png':
                    # 冰港道具图集的行间空隙在高度的 45% 处。
                    split = round(height * .45)
                    top, bottom = (0, split) if row == 0 else (split, height)
                if filename == 'moss-props.png':
                    left, right, top, bottom = left + 12, right - 12, top + 12, bottom - 12
                sprite = atlas.subsurface((left, top, right - left, bottom - top))
                self.images[key] = sprite.subsurface(sprite.get_bounding_rect(min_alpha=12)).copy()
        duck = pygame.image.load(str(ROOT / 'assets' / 'harbor-duck.png')).convert_alpha()
        self.images['rubber_duck'] = duck.subsurface(duck.get_bounding_rect(min_alpha=12)).copy()
        self.forest_background = pygame.transform.smoothscale(
            pygame.image.load(str(ROOT / 'assets' / 'forest-garden.png')).convert(), (WIDTH, HEIGHT))
        self.bay_background = pygame.transform.smoothscale(
            pygame.image.load(str(ROOT / 'assets' / 'bay-water.png')).convert(), (WIDTH, HEIGHT))
        self.maps = {}
        self.set_map(map_config(0))

    def set_map(self, layout):
        routes = layout.get('routes', (layout['path'],))
        key = layout['theme'], tuple(tuple(route) for route in routes)
        if key not in self.maps:
            self.maps[key] = self.make_map(layout)
        self.map = self.maps[key]

    def sprite(self, surface, key, center, size, angle=0, *, feet=False):
        cache_key = key, size
        if cache_key not in self.scaled:
            image = self.images[key]
            ratio = min(size[0] / image.get_width(), size[1] / image.get_height())
            self.scaled[cache_key] = pygame.transform.smoothscale(
                image, (max(1, round(image.get_width() * ratio)), max(1, round(image.get_height() * ratio))))
        image = self.scaled[cache_key]
        if angle:
            image = pygame.transform.rotate(image, angle)
        rect = image.get_rect(midbottom=center) if feet else image.get_rect(center=center)
        surface.blit(image, rect)

    def make_map(self, layout):
        if layout['theme'] == 'ice':
            return self.make_ice_map(layout)
        if layout['theme'] == 'forest':
            return self.make_forest_map(layout)
        if layout['theme'] == 'bay':
            return self.make_bay_map(layout)
        if layout['theme'] == 'strait':
            return self.make_strait_map(layout)
        if layout['theme'] == 'moss':
            return self.make_moss_map(layout)
        if layout['theme'] == 'snow':
            return self.make_snow_map(layout)
        if layout['theme'] == 'desert':
            return self.make_desert_map(layout)
        path = layout['path']
        surface = self.background.copy()
        # 渲染与敌人移动共用路径点，保证视觉道路和实际路线一致。
        route = []
        for a, b in zip(path, path[1:]):
            a, b = pygame.Vector2(a), pygame.Vector2(b)
            steps = max(1, round(a.distance_to(b) / 18))
            route.extend(a.lerp(b, i / steps) for i in range(steps))
        route.append(pygame.Vector2(path[-1]))
        for color, radius, offset in [((132, 99, 166), 33, 9), ((217, 181, 233), 32, 4), ((253, 228, 243), 30, 0)]:
            pygame.draw.lines(surface, color, False, [(x, y + offset) for x, y in path], radius * 2)
            for i, p in enumerate(route):
                pygame.draw.circle(surface, color, (p.x, p.y + offset), radius + (i % 3 == 0) * 3)
        for a, b in zip(path, path[1:]):
            a, b = pygame.Vector2(a), pygame.Vector2(b)
            steps = int(a.distance_to(b) / 34)
            for i in range(1, steps):
                p = a.lerp(b, i / steps)
                pygame.draw.circle(surface, (238, 201, 225), p, 3)
        rng = random.Random(12)
        for _ in range(35):
            x, y = rng.randrange(45, WIDTH - 30), rng.randrange(120, 710)
            if all(pygame.Vector2(x, y).distance_to(p) > 52 for p in route):
                star(surface, (x, y), rng.randrange(3, 6), (242, 225, 250))
        x, y = path[0]
        pygame.draw.line(surface, (135, 94, 138), (x + 15, y - 28), (x + 15, y - 70), 7)
        panel(surface, (10, y - 83, 84, 38), (255, 215, 143), (182, 129, 122), 12)
        text(surface, '怪兽入口', (52, y - 64), 15, center=True, bold=True)
        return surface

    def make_ice_map(self, layout):
        surface = self.ice_background.copy()
        self.draw_tile_route(surface, layout)
        return surface

    def make_snow_map(self, layout):
        surface = pygame.Surface((WIDTH, HEIGHT))
        for x in range(WIDTH):
            glow = math.sin(math.pi * x / WIDTH) ** 2
            pygame.draw.line(surface, (round(18 + glow * 14), round(128 + glow * 66),
                                       round(197 + glow * 33)), (x, 0), (x, HEIGHT))
        rng = random.Random(67)
        for _ in range(520):
            x, y = rng.randrange(WIDTH), rng.randrange(90, HEIGHT)
            radius = rng.randrange(1, 5)
            color = surface.get_at((x, y))
            tint = (min(255, color.r + 18), min(255, color.g + 20), min(255, color.b + 15))
            pygame.draw.circle(surface, tint, (x, y), radius)
        self.draw_tile_route(surface, layout)
        return surface

    def draw_tile_route(self, surface, layout):
        ice = ((72, 159, 175), (201, 247, 250), (97, 191, 212),
               (245, 255, 255), (156, 222, 231), (175, 232, 242))
        stone = ((85, 99, 63), (194, 194, 164), (160, 164, 132),
                 (221, 221, 194), (166, 170, 139), (173, 177, 146))
        sandstone = ((159, 104, 41), (222, 175, 94), (178, 117, 51),
                     (249, 210, 132), (193, 139, 64), (235, 192, 106))
        palettes = {'moss': stone, 'desert': sandstone}
        shadow, fill, edge, shine, crack, fleck = palettes.get(layout['theme'], ice)
        rng = random.Random(22)
        for col, row in sorted(layout['path_cells']):
            x, y = GRID_X + col * TILE, GRID_Y + row * TILE
            panel(surface, (x - 2, y + 5, TILE + 4, TILE), shadow, radius=10)
        for col, row in sorted(layout['path_cells']):
            x, y = GRID_X + col * TILE, GRID_Y + row * TILE
            panel(surface, (x + 1, y, TILE - 2, TILE - 2), fill, edge, 9)
            pygame.draw.line(surface, shine, (x + 10, y + 5), (x + 49, y + 5), 3)
            if rng.random() < .4:
                pygame.draw.lines(surface, crack, False,
                                  [(x + 46, y + 58), (x + 41, y + 49), (x + 46, y + 43)], 2)
            pygame.draw.circle(surface, fleck, (x + 18, y + 39), 2)
        routes = layout.get('routes', (layout['path'],))
        names = ('怪兽入口',) if len(routes) == 1 else ('左侧入口', '右侧入口')
        for route, name in zip(routes, names):
            x, y = route[0]
            sign_x = max(8, x - 45)
            pygame.draw.line(surface, (150, 102, 72), (sign_x + 45, y - 24), (sign_x + 45, y - 65), 6)
            panel(surface, (sign_x, y - 82, 90, 36), (255, 230, 173), (191, 142, 87), 10)
            text(surface, name, (sign_x + 45, y - 65), 15, center=True, bold=True)

    def make_strait_map(self, layout):
        surface = self.bay_background.copy()
        surface.fill((16, 39, 27), special_flags=pygame.BLEND_RGB_ADD)
        self.draw_tile_route(surface, layout)
        return surface

    def make_moss_map(self, layout):
        surface = self.forest_background.copy()
        surface.fill((122, 154, 111), special_flags=pygame.BLEND_RGB_MULT)
        for x, y, size in [(10, 158, 110), (18, 334, 103), (9, 535, 124), (22, 696, 125),
                           (1269, 186, 118), (1260, 375, 105), (1271, 540, 128), (1262, 705, 115)]:
            self.sprite(surface, 'moss_rock', (x, y), (size, size))
        self.draw_tile_route(surface, layout)
        return surface

    def make_desert_map(self, layout):
        background = pygame.image.load(str(ROOT / 'assets' / 'desert-background.png')).convert()
        surface = pygame.transform.smoothscale(background, (WIDTH, HEIGHT))
        self.draw_tile_route(surface, layout)
        return surface

    def turret(self, surface, kind, center, angle=-45, kick=0, preview=False):
        head = f'{kind}-head'
        if head not in self.images:
            if preview:
                self.sprite(surface, kind, center, (61, 61))
            else:
                self.sprite(surface, kind, (center[0], center[1] - 6), (62, 72))
            return
        self.sprite(surface, 'turret-base', center, (56, 56))
        direction = pygame.Vector2(1, 0).rotate(angle)
        pivot = pygame.Vector2(center) - direction * kick
        self.sprite(surface, head, pivot, (53, 49), -angle)

    def make_bay_map(self, layout):
        surface = self.bay_background.copy()
        for offset, color in [(20, (16, 79, 150)), (12, (30, 126, 190)), (6, (67, 173, 222))]:
            pygame.draw.polygon(surface, color, [(x, y + offset) for x, y in BAY_SHORE])
        pygame.draw.polygon(surface, (142, 214, 241), BAY_SHORE)
        for color, points in [
            ((169, 230, 249), [(244, 253), (305, 126), (465, 109), (580, 180), (403, 273), (218, 340)]),
            ((151, 222, 247), [(580, 180), (748, 105), (915, 140), (995, 224), (822, 322), (650, 305)]),
            ((159, 225, 246), [(195, 457), (362, 418), (548, 487), (493, 712), (328, 679), (230, 606)]),
            ((123, 203, 235), [(700, 716), (852, 678), (972, 604), (1089, 543), (1134, 473), (880, 529)]),
        ]:
            pygame.draw.polygon(surface, color, points)
        pygame.draw.lines(surface, (207, 248, 255), True, BAY_SHORE, 4)
        pygame.draw.aalines(surface, (225, 251, 255), True, BAY_SHORE)
        for x, y in [(332, 581), (462, 636), (781, 583), (837, 295), (532, 369), (973, 474)]:
            pygame.draw.aalines(surface, (192, 239, 254), False,
                                [(x - 20, y + 7), (x, y), (x + 15, y + 6), (x + 24, y + 1)])
        self.draw_tile_route(surface, layout)
        return surface

    def make_forest_map(self, layout):
        surface = self.forest_background.copy()
        path = layout['path']
        for color, radius in [((84, 124, 40), 35), ((144, 98, 37), 32), ((192, 140, 57), 28)]:
            pygame.draw.lines(surface, color, False, path, radius * 2)
            for point in path:
                pygame.draw.circle(surface, color, point, radius)
        rng = random.Random(33)
        for a, b in zip(path, path[1:]):
            a, b = pygame.Vector2(a), pygame.Vector2(b)
            for i in range(1, max(2, round(a.distance_to(b) / 31))):
                p = a.lerp(b, i / max(2, round(a.distance_to(b) / 31)))
                p += pygame.Vector2(rng.randrange(-11, 12), rng.randrange(-11, 12))
                pygame.draw.circle(surface, (174, 121, 44), p, rng.randrange(4, 10))
        x, y = path[0]
        sign_x = max(53, x)
        pygame.draw.line(surface, (114, 82, 41), (sign_x, y - 29), (sign_x, y - 65), 6)
        panel(surface, (sign_x - 45, y - 82, 90, 36), (255, 225, 147), (158, 110, 56), 10)
        text(surface, '怪兽入口', (sign_x, y - 65), 15, center=True, bold=True)
        return surface

    def draw_boss(self, surface, enemy, tick):
        x, y = enemy.position
        pygame.draw.ellipse(surface, (132, 95, 148), (x - 43, y + 22, 86, 20))
        self.sprite(surface, 'boss', (x, y - 12 + math.sin(tick * 5) * 3), (108, 106))
        draw_slow_crystals(surface, enemy, tick, 1.8)

    def draw_obstacle(self, surface, obstacle, selected=False, *, theme='cloud'):
        x, y = obstacle.position
        bounds = obstacle.bounds
        icy = obstacle.kind in ('igloo', 'iceberg', 'icecrystal', 'snowtrees', 'lighthouse', 'rowboat',
                                'driftwood', 'lifebuoy', 'message_bottle', 'ice_pop', 'rubber_duck',
                                'cupcake', 'winter_hat', 'coin_pouch', 'snow_logs',
                                'snow_bush', 'pink_pop')
        woodland = obstacle.kind in ('stump', 'rocks', 'forest', 'windmill', 'pine')
        moss = obstacle.kind in ('acorn', 'moss_rock', 'rope_fence', 'spring_pool')
        shadow = (94, 177, 182) if icy else ((68, 104, 53) if woodland or moss else (163, 137, 181))
        if theme == 'desert':
            shadow = (186, 135, 64)
        pygame.draw.ellipse(surface, shadow, (bounds.left + 7, bounds.bottom - 18, bounds.width - 14, 14))
        if selected:
            pygame.draw.rect(surface, (255, 247, 202), bounds.inflate(-3, -3), 2, border_radius=8)
        size = (64, 75) if obstacle.kind in ('trees', 'crystal', 'chest') else (
            bounds.width - 4, bounds.height - 5)
        feet = moss or theme == 'desert'
        anchor = (x, bounds.bottom - 10) if feet else (x, y - 4)
        if obstacle.kind == 'cupcake' and obstacle.width == 2:
            self.sprite(surface, 'cupcake', (x - 23, bounds.bottom - 8), (62, 59), feet=True)
            self.sprite(surface, 'cupcake', (x + 27, bounds.bottom - 8), (47, 44), feet=True)
        else:
            self.sprite(surface, obstacle.kind, anchor, size, feet=feet)
        if selected or obstacle.hp < obstacle.max_hp:
            width = min(90, bounds.width - 10)
            panel(surface, (x - width / 2, bounds.top - 11, width, 7), PLUM, radius=3)
            panel(surface, (x - width / 2, bounds.top - 11, max(1, width * obstacle.hp / obstacle.max_hp), 7), (132, 238, 169), radius=3)


def draw_effect(surface, effect, tick, art):
    """弹丸与命中分开绘制，光圈以太阳为中心，星芒以命中点为中心。"""
    if effect.kind == 'fan':
        art.sprite(surface, 'fan-flight', effect.position, (42, 42), tick * -680 % 360)
        return
    if effect.kind == 'rocket':
        angle = -math.degrees(math.atan2(effect.direction.y, effect.direction.x))
        art.sprite(surface, 'rocket-flight', effect.position, (50, 28), angle)
        return
    if effect.kind == 'arrow':
        draw_arrow_volley(surface, effect)
        return
    if hasattr(effect, 'position'):
        point = effect.position
        direction = pygame.Vector2(effect.end) - point
        if direction.length_squared():
            direction = direction.normalize()
        for i in range(4, 0, -1):
            trail = point - direction * (i * 7)
            color = (249, 194 + i * 8, 104 + i * 19)
            pygame.draw.circle(surface, color, trail, max(2, 7 - i))
        if effect.kind == 'bottle':
            pygame.draw.circle(surface, (240, 152, 34), point, 10)
            pygame.draw.circle(surface, (255, 216, 66), point, 8)
            pygame.draw.circle(surface, (255, 250, 169), point, 5)
            pygame.draw.circle(surface, WHITE, (point.x - 2, point.y - 3), 3)
        else:
            rotation = tick * 4 - math.pi / 2
            star(surface, point, 18, (205, 127, 28), rotation)
            star(surface, point, 15, (255, 218, 57), rotation)
            for i in range(5):
                angle = rotation + i * math.tau / 5
                tip = (point.x + math.cos(angle) * 14, point.y + math.sin(angle) * 14)
                inner = (point.x + math.cos(angle + math.pi / 5) * 6,
                         point.y + math.sin(angle + math.pi / 5) * 6)
                pygame.draw.polygon(surface, (255, 246, 155), [point, tip, inner])
        return
    if effect.kind == 'moon':
        progress = 1 - max(0, effect.life / .55)
        radius = max(3, round(effect.radius * (.2 + .8 * min(1, progress * 1.3))))
        alpha = round(230 * (1 - progress ** 3))
        glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for width, color in [(20, (103, 125, 250, alpha // 3)),
                             (12, (108, 194, 255, alpha)),
                             (6, (167, 237, 255, alpha)),
                             (2, (234, 253, 255, alpha))]:
            pygame.draw.circle(glow, color, effect.end, radius, min(width, radius))
        pygame.draw.circle(glow, (161, 220, 255, alpha // 2), effect.end, max(2, radius - 17), 2)
        surface.blit(glow, (0, 0))
    elif effect.kind == 'sun':
        progress = 1 - max(0, effect.life / .55)
        radius = effect.radius * (.30 + .70 * min(1, progress * 1.3))
        points = []
        for i in range(120):
            angle = i * math.tau / 120
            wave = .96 + .04 * math.sin(angle * 12 + tick * 5)
            points.append((effect.end[0] + math.cos(angle) * radius * wave,
                           effect.end[1] + math.sin(angle) * radius * wave))
        glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        alpha = max(0, round(220 * (1 - progress ** 3)))
        pygame.draw.polygon(glow, (255, 214, 75, int(alpha * .09)), points)
        pygame.draw.lines(glow, (255, 143, 23, int(alpha * .4)), True, points, 20)
        pygame.draw.lines(glow, (255, 195, 26, alpha), True, points, 11)
        pygame.draw.lines(glow, (255, 248, 106, alpha), True, points, 6)
        pygame.draw.lines(glow, (255, 255, 221, alpha), True, points, 2)
        surface.blit(glow, (0, 0))
    elif effect.kind == 'star_hit':
        progress = 1 - effect.life / .30
        radius = max(2, int(effect.radius * progress))
        pygame.draw.circle(surface, (255, 228, 115), effect.end, radius, 3)
        for i in range(7):
            angle = i * math.tau / 7 + tick
            point = (effect.end[0] + math.cos(angle) * radius,
                     effect.end[1] + math.sin(angle) * radius)
            star(surface, point, 6, (255, 237, 143), angle)
    elif effect.kind == 'bean_hit':
        pygame.draw.circle(surface, (255, 234, 137), effect.end,
                           max(2, round(12 * (1 - effect.life / .16))), 2)


def draw_arrow_volley(surface, effect):
    start, end = pygame.Vector2(effect.start), pygame.Vector2(effect.end)
    if effect.life <= .13:
        radius = max(3, int(effect.radius * (1 - effect.life / .13)))
        pygame.draw.circle(surface, (191, 133, 248), end, radius, 2)
        return
    axis = end - start
    direction = axis.normalize() if axis.length_squared() else pygame.Vector2(1, 0)
    normal = direction.rotate(90)
    progress = max(0, min(1, (.39 - effect.life) / .26))
    for lane in (-1, 0, 1):
        origin = start + normal * (lane * 3)
        destination = end + normal * (lane * 23)
        travel = destination - origin
        forward = travel.normalize() if travel.length_squared() else direction
        side = forward.rotate(90)
        tip = origin.lerp(destination, progress)
        tail = tip - forward * 26
        pygame.draw.line(surface, (118, 64, 199), tail, tip, 6)
        pygame.draw.line(surface, (214, 160, 255), tail, tip, 2)
        head = tip - forward * 10
        pygame.draw.polygon(surface, (180, 103, 252), [tip, head + side * 6, head - side * 6])
        pygame.draw.line(surface, (249, 218, 255), head + side * 4, tip, 2)
        pygame.draw.lines(surface, (206, 148, 255), False,
                          [tail + side * 5, tail + forward * 6, tail - side * 5], 2)


def draw_laser(surface, start, end, tick):
    start, end = pygame.Vector2(start), pygame.Vector2(end)
    direction = end - start
    normal = pygame.Vector2(-direction.y, direction.x)
    if normal.length_squared():
        normal = normal.normalize()
    points = [start]
    for i in range(1, 15):
        points.append(start.lerp(end, i / 15) + normal * math.sin(i * 2.7 + tick * 35) * 6)
    points.append(end)
    glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.lines(glow, (161, 55, 247, 65), False, points, 16)
    pygame.draw.lines(glow, (200, 100, 255, 150), False, points, 8)
    surface.blit(glow, (0, 0))
    pygame.draw.lines(surface, (209, 133, 255), False, points, 5)
    pygame.draw.lines(surface, (255, 232, 255), False, points, 2)
    star(surface, end, 11, (243, 197, 255), tick * 5)


def draw_slow_crystals(surface, enemy, tick, scale=1):
    source = enemy.slow_source
    if source is None:
        return
    x, y = enemy.position
    blue = source == 'moon'
    outline = (93, 113, 228) if blue else (26, 169, 113)
    body = (143, 199, 255) if blue else (84, 232, 154)
    shine = (222, 246, 255) if blue else (198, 255, 213)
    for i in range(5):
        cx = x + (i - 2) * 10 * scale
        bottom = y + (21 + (i % 2) * 2) * scale
        height = (25 + (i % 3) * 5) * scale
        w = 6 * scale
        tip = (cx + 3 * scale, bottom - height)
        points = [(cx - w, bottom - 8 * scale), tip,
                  (cx + w, bottom - height * .5), (cx + w - 2, bottom), (cx - w, bottom)]
        pygame.draw.polygon(surface, body, points)
        pygame.draw.polygon(surface, outline, points, 2)
        pygame.draw.lines(surface, shine, False, [tip, (cx, bottom - 9 * scale), (cx - w, bottom)], 2)


def draw_enemy(surface, enemy, tick, art):
    x, y = enemy.position
    y += math.sin(tick * 8 + enemy.progress * .03) * 2
    dango = enemy.kind in DANGO_KINDS
    width, height = (67, 49) if dango else (48, 49)
    pygame.draw.ellipse(surface, (127, 108, 157), (x - width * .35, y + 16, width * .7, 8))
    key = FOOD_GROUPS[enemy.kind][0] if enemy.kind in FOOD_GROUPS else enemy.kind
    art.sprite(surface, key, (x, y + 20), (width, height), feet=True)
    if enemy.hp < enemy.max_hp:
        bar = 52 if dango else 40
        panel(surface, (x - bar / 2, y - 36, bar, 5), PLUM, radius=2)
        panel(surface, (x - bar / 2, y - 36, max(1, bar * enemy.hp / enemy.max_hp), 5),
              (132, 238, 169), radius=2)
    draw_slow_crystals(surface, enemy, tick)
