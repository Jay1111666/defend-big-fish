"""关卡与战斗数值。距离单位为像素，时间单位为秒。"""
WIDTH, HEIGHT = 1280, 800
TILE = 64
COLS, ROWS = 18, 9
GRID_X, GRID_Y = 64, 128
PATH_GRID = [(-1, 2), (3, 2), (3, 6), (8, 6), (8, 1),
             (12, 1), (12, 5), (16, 5), (16, 3)]
PATH = [(GRID_X + (col + .5) * TILE, GRID_Y + (row + .5) * TILE)
        for col, row in PATH_GRID]
PADS = [(GRID_X + (col + .5) * TILE, GRID_Y + (row + .5) * TILE)
        for row in range(ROWS) for col in range(COLS)]
PATH_CELLS = set()
for (ax, ay), (bx, by) in zip(PATH_GRID, PATH_GRID[1:]):
    PATH_CELLS.update((col, row)
                      for col in range(min(ax, bx), max(ax, bx) + 1)
                      for row in range(min(ay, by), max(ay, by) + 1))
OBSTACLES = {
    (1, 0): 'trees', (6, 1): 'trees', (5, 4): 'trees',
    (1, 7): 'trees', (10, 7): 'trees', (15, 7): 'trees',
    (6, 3): 'crystal', (10, 3): 'crystal', (14, 2): 'crystal',
    (17, 7): 'crystal', (1, 5): 'chest', (6, 7): 'chest', (14, 6): 'chest',
}
# 每项为 (种类, 左上角列, 左上角行, 占用宽度, 占用高度)。
CLOUD_OBSTACLES = [
    ('balloon_basket', 4, 0, 2, 2), ('balloon_basket', 9, 5, 2, 2),
    ('rainbow_cloud', 4, 7, 2, 1), ('gold_planet', 14, 3, 1, 1),
    ('orange_planet', 13, 8, 1, 1), ('cloud_trees', 2, 0, 2, 2),
]
OBSTACLE_STATS = {
    'trees': dict(name='星糖树', hp=140, reward=12),
    'crystal': dict(name='水晶', hp=200, reward=16),
    'chest': dict(name='宝箱', hp=240, reward=22),
    'igloo': dict(name='冰屋', hp=360, reward=32),
    'iceberg': dict(name='冰岩', hp=250, reward=23),
    'icecrystal': dict(name='冰晶', hp=110, reward=10),
    'snowtrees': dict(name='雪松', hp=280, reward=26),
    'stump': dict(name='树桩', hp=160, reward=15),
    'rocks': dict(name='岩石堆', hp=250, reward=23),
    'forest': dict(name='彩叶松林', hp=300, reward=28),
    'windmill': dict(name='风车小屋', hp=400, reward=36),
    'lighthouse': dict(name='海湾灯塔', hp=420, reward=40),
    'rowboat': dict(name='搁浅小艇', hp=260, reward=24),
    'driftwood': dict(name='漂流木', hp=180, reward=17),
    'lifebuoy': dict(name='救生圈', hp=120, reward=12),
    'message_bottle': dict(name='漂流瓶', hp=180, reward=17),
    'ice_pop': dict(name='冰棍', hp=210, reward=20),
    'rubber_duck': dict(name='橡皮鸭', hp=330, reward=32),
    'acorn': dict(name='橡果', hp=120, reward=12),
    'moss_rock': dict(name='苔石', hp=190, reward=17),
    'rope_fence': dict(name='绳栏', hp=240, reward=22),
    'spring_pool': dict(name='碧泉', hp=220, reward=21),
    'balloon_basket': dict(name='气球篮', hp=250, reward=24),
    'rainbow_cloud': dict(name='彩虹云', hp=170, reward=16),
    'gold_planet': dict(name='金环星', hp=145, reward=14),
    'orange_planet': dict(name='橘环星', hp=145, reward=14),
    'cloud_trees': dict(name='云上双松', hp=200, reward=19),
    'cupcake': dict(name='樱桃奶油塔', hp=140, reward=13),
    'winter_hat': dict(name='绒球雪帽', hp=115, reward=11),
    'coin_pouch': dict(name='金币袋', hp=155, reward=22),
    'snow_logs': dict(name='积雪圆木', hp=220, reward=21),
    'green_cactus': dict(name='绿仙人掌', hp=115, reward=11),
    'orange_cactus': dict(name='橘仙人掌', hp=120, reward=12),
    'tall_cactus': dict(name='柱形仙人掌', hp=285, reward=27),
    'sandstone': dict(name='砂岩堆', hp=190, reward=17),
    'sandstone_small': dict(name='小砂岩', hp=115, reward=10),
    'ram_skull': dict(name='羊角遗骨', hp=180, reward=17),
    'desert_well': dict(name='沙漠水井', hp=310, reward=29),
    'pine': dict(name='青松', hp=130, reward=12),
    'snow_bush': dict(name='雪顶灌木', hp=145, reward=13),
    'pink_pop': dict(name='草莓冰棍', hp=155, reward=14),
}
# 角色立绘与终点周围保留空间，避免塔覆盖角色。
HOME_CELLS = {(col, row) for col in range(15, 18) for row in range(5)}
BLOCKED_CELLS = PATH_CELLS | set(OBSTACLES) | HOME_CELLS | {
    (col + dx, row + dy)
    for _, col, row, width, height in CLOUD_OBSTACLES
    for dx in range(width) for dy in range(height)
}

ICE_PATH_GRID = [(-1, 6), (2, 6), (2, 3), (6, 3), (6, 6),
                 (10, 6), (10, 2), (14, 2), (14, 7), (16, 7)]
ICE_OBSTACLES = [
    ('igloo', 0, 0, 2, 2), ('igloo', 4, 0, 2, 2),
    ('igloo', 8, 0, 2, 2), ('igloo', 11, 4, 2, 2),
    ('iceberg', 3, 7, 2, 1), ('iceberg', 7, 4, 2, 1),
    ('iceberg', 11, 0, 2, 1), ('iceberg', 11, 7, 2, 1),
    ('snowtrees', 3, 4, 2, 2), ('snowtrees', 7, 7, 2, 2),
    ('snowtrees', 15, 0, 2, 2),
] + [('icecrystal', col, row, 1, 1) for col, row in [
    (0, 3), (0, 4), (1, 2), (4, 2), (7, 2), (8, 3), (9, 4),
    (11, 3), (13, 1), (16, 3), (17, 4), (5, 7), (1, 8),
    (0, 7), (12, 6), (17, 2),
]]

FOREST_PATH_GRID = [(-1, 6), (7, 6), (7, 8), (10, 8), (10, 4),
                    (3, 4), (3, 1), (14, 1), (14, 6), (16, 6)]
FOREST_OBSTACLES = [
    ('windmill', 0, 1, 2, 2), ('windmill', 11, 5, 2, 2),
    ('forest', 15, 0, 2, 2), ('forest', 5, 2, 2, 2),
    ('forest', 5, 7, 2, 2), ('forest', 0, 7, 2, 2),
] + [('rocks', col, row, 2, 1) for col, row in [
    (4, 0), (9, 0), (11, 2), (0, 4), (8, 5), (11, 7),
]] + [('stump', col, row, 1, 1) for col, row in [
    (1, 0), (7, 0), (13, 0), (4, 5), (1, 5), (8, 3),
    (12, 4), (13, 8), (3, 7), (17, 8), (4, 3), (3, 0),
]]
BAY_SHORE = [(195, 457), (218, 340), (244, 253), (305, 126), (465, 109),
             (748, 105), (915, 140), (995, 224), (1031, 315), (1119, 371),
             (1134, 473), (1089, 543), (972, 604), (852, 678), (700, 716),
             (493, 712), (328, 679), (230, 606)]
BAY_PATH_GRID = [(15, 4), (12, 4), (12, 7), (9, 7), (9, 1),
                 (6, 1), (6, 4), (3, 4)]
BAY_OBSTACLES = [
    ('lighthouse', 5, 0, 1, 2), ('rowboat', 13, 5, 2, 1),
    ('rowboat', 4, 7, 2, 1), ('driftwood', 10, 2, 2, 1),
    ('driftwood', 7, 6, 2, 1), ('snowtrees', 7, 2, 2, 2),
    ('snowtrees', 10, 0, 2, 2), ('iceberg', 3, 5, 2, 1),
    ('chest', 6, 6, 1, 1), ('chest', 13, 2, 1, 1),
    ('icecrystal', 8, 0, 1, 1), ('icecrystal', 5, 2, 1, 1),
    ('icecrystal', 10, 6, 1, 1), ('icecrystal', 7, 8, 1, 1),
    ('icecrystal', 12, 3, 1, 1), ('driftwood', 8, 4, 1, 1),
]

STRAIT_PATH_GRIDS = (
    [(7, 4), (7, 1), (3, 1), (3, 7), (8, 7), (8, 6)],
    [(10, 4), (10, 1), (14, 1), (14, 7), (8, 7), (8, 6)],
)
STRAIT_OBSTACLES = [
    ('message_bottle', 2, 0, 2, 1), ('message_bottle', 11, 0, 2, 1),
    ('message_bottle', 3, 8, 2, 1), ('ice_pop', 0, 2, 2, 2),
    ('ice_pop', 11, 4, 2, 2), ('rubber_duck', 15, 2, 2, 2),
    ('rubber_duck', 4, 4, 2, 2), ('iceberg', 0, 5, 2, 1),
    ('iceberg', 7, 8, 2, 1), ('rowboat', 15, 5, 2, 1),
    ('rowboat', 10, 8, 2, 1), ('icecrystal', 0, 7, 2, 2),
    ('icecrystal', 16, 7, 2, 2),
] + [
    (kind, col, row, 1, 1)
    for kind, cells in [
        ('lifebuoy', [(6, 0), (10, 0), (15, 0), (4, 2), (6, 2),
                      (11, 2), (13, 2), (7, 6), (10, 6)]),
        ('icecrystal', [(5, 0), (9, 0), (2, 6), (13, 8)]),
        ('ice_pop', [(13, 0), (15, 7)]),
    ]
    for col, row in cells
]

MOSS_PATH_GRID = [(15, 6), (15, 1), (12, 1), (12, 6), (9, 6), (9, 4),
                  (10, 4), (10, 1), (5, 1), (5, 0), (2, 0), (2, 2),
                  (7, 2), (7, 4), (1, 4), (1, 8), (4, 8)]
MOSS_OBSTACLES = [
    ('rope_fence', 6, 0, 2, 1), ('rope_fence', 11, 0, 2, 1),
    ('rope_fence', 14, 0, 2, 1), ('rope_fence', 13, 8, 2, 1),
    ('spring_pool', 10, 5, 2, 1), ('spring_pool', 7, 8, 2, 1),
    ('spring_pool', 10, 8, 2, 1),
] + [
    (kind, col, row, 1, 1)
    for kind, cells in [
        ('acorn', [(1, 0), (3, 1), (8, 3), (13, 2), (16, 2), (13, 5), (16, 6), (6, 6), (9, 8)]),
        ('moss_rock', [(0, 1), (0, 2), (11, 1), (16, 5), (5, 5), (0, 7), (17, 7)]),
        ('spring_pool', [(9, 0), (13, 0), (16, 0), (11, 3), (13, 4), (16, 4), (7, 5), (8, 5)]),
    ]
    for col, row in cells
]

SNOW_PATH_GRID = [(2, 7), (2, 4), (6, 4), (6, 7), (9, 7),
                  (9, 1), (15, 1), (15, 7), (12, 7)]
SNOW_OBSTACLES = [
    ('igloo', 7, 2, 2, 2), ('igloo', 10, 3, 2, 2),
    ('snowtrees', 2, 1, 2, 2), ('snowtrees', 13, 2, 2, 2),
    ('snow_logs', 4, 0, 2, 1), ('snow_logs', 12, 0, 2, 1),
    ('iceberg', 9, 0, 2, 1), ('iceberg', 2, 8, 2, 1),
    ('iceberg', 6, 8, 2, 1), ('iceberg', 10, 8, 2, 1),
    ('iceberg', 14, 8, 2, 1), ('cupcake', 13, 4, 2, 1),
] + [
    (kind, col, row, 1, 1)
    for kind, cells in [
        ('snowtrees', [(3, 0), (7, 0), (11, 0), (15, 0),
                       (1, 3), (5, 3), (1, 6), (16, 3)]),
        ('coin_pouch', [(1, 0), (2, 0), (1, 1), (16, 0), (16, 6)]),
        ('winter_hat', [(3, 6), (4, 6)]),
        ('cupcake', [(8, 4), (8, 5)]),
    ]
    for col, row in cells
]

DESERT_PATH_GRID = [(3, 6), (3, 3), (6, 3), (6, 6), (9, 6),
                    (9, 3), (12, 3), (12, 6), (15, 6), (15, 3)]
DESERT_OBSTACLES = [
    ('tall_cactus', 0, 1, 2, 2), ('coin_pouch', 2, 0, 2, 2),
    ('ram_skull', 5, 1, 2, 1), ('ram_skull', 15, 0, 2, 1),
    ('spring_pool', 0, 4, 2, 1), ('spring_pool', 6, 7, 2, 1),
    ('coin_pouch', 16, 5, 2, 2), ('desert_well', 13, 7, 2, 2),
    ('sandstone', 10, 7, 2, 1), ('sandstone', 6, 8, 2, 1),
] + [
    (kind, col, row, 1, 1)
    for kind, cells in [
        ('green_cactus', [(10, 0), (9, 1), (11, 1)]),
        ('orange_cactus', [(9, 0), (11, 0), (10, 1)]),
        ('coin_pouch', [(4, 6), (10, 6), (2, 7), (3, 7), (4, 7), (13, 3), (17, 3)]),
        ('sandstone_small', [(7, 3), (8, 7)]),
    ]
    for col, row in cells
]

WINDMILL_PATH_GRID = [(6, 1), (6, 2), (2, 2), (2, 7), (5, 7),
                     (5, 5), (9, 5), (9, 2), (13, 2), (13, 6), (16, 6)]
WINDMILL_OBSTACLES = [
    ('windmill', 3, 0, 2, 2), ('windmill', 10, 3, 2, 2),
    ('rocks', 3, 3, 2, 1), ('rocks', 13, 8, 2, 1),
    ('spring_pool', 6, 3, 2, 1), ('spring_pool', 14, 2, 2, 1),
    ('forest', 9, 0, 2, 2), ('forest', 14, 0, 2, 2),
    ('forest', 6, 7, 2, 2), ('forest', 10, 7, 2, 2), ('stump', 11, 1, 2, 1),
] + [
    ('pine', col, row, 1, 1)
    for col, row in [(0, 0), (1, 0), (0, 1), (1, 1), (7, 0), (7, 1), (7, 2),
                     (11, 0), (12, 0), (16, 0), (16, 1), (0, 3), (0, 6),
                     (3, 5), (3, 6), (9, 6), (9, 8), (16, 8), (14, 4), (14, 5),
                     (17, 2)]
] + [('rocks', 0, 5, 1, 1)]

ICE_FINALE_PATH_GRID = [(15, 6), (15, 0), (14, 0), (14, 6), (9, 6), (9, 5),
                        (8, 5), (8, 4), (7, 4), (7, 2), (6, 2), (6, 1),
                        (5, 1), (5, 0), (4, 0), (4, 1), (3, 1), (3, 2),
                        (4, 2), (4, 4), (5, 4), (5, 5), (6, 5), (6, 6),
                        (7, 6), (7, 8), (8, 8)]
ICE_FINALE_OBSTACLES = [
    ('iceberg', 1, 0, 2, 1), ('iceberg', 10, 1, 2, 1), ('iceberg', 10, 8, 2, 1),
    ('igloo', 7, 0, 2, 2), ('igloo', 10, 3, 2, 2),
    ('igloo', 1, 3, 2, 2), ('igloo', 4, 7, 2, 2),
] + [
    (kind, col, row, 1, 1)
    for kind, cells in [
        ('icecrystal', [(2, 1), (2, 2), (1, 6), (2, 6), (6, 8)]),
        ('pink_pop', [(6, 0), (5, 2), (6, 4), (8, 2), (7, 5), (10, 5)]),
        ('snow_bush', [(12, 0), (12, 2), (12, 5), (16, 1), (16, 3), (16, 6)]),
    ]
    for col, row in cells
]


def on_bay_land(x, y):
    inside = False
    for (ax, ay), (bx, by) in zip(BAY_SHORE, BAY_SHORE[1:] + BAY_SHORE[:1]):
        if (ay > y) != (by > y) and x < ax + (bx - ax) * (y - ay) / (by - ay):
            inside = not inside
    return inside


def map_config(index):
    special_maps = {
        1: ('ice', ICE_PATH_GRID, ICE_OBSTACLES, range(15, 18), range(5, 9)),
        2: ('forest', FOREST_PATH_GRID, FOREST_OBSTACLES, range(15, 18), range(3, 8)),
        3: ('bay', BAY_PATH_GRID, BAY_OBSTACLES, range(2, 5), range(1, 5)),
        4: ('strait', STRAIT_PATH_GRIDS[0], STRAIT_OBSTACLES, range(8, 10), range(3, 7)),
        5: ('moss', MOSS_PATH_GRID, MOSS_OBSTACLES, range(3, 6), range(6, 9)),
        6: ('snow', SNOW_PATH_GRID, SNOW_OBSTACLES, range(11, 14), range(5, 8)),
        7: ('desert', DESERT_PATH_GRID, DESERT_OBSTACLES, range(14, 17), range(1, 4)),
        8: ('forest', WINDMILL_PATH_GRID, WINDMILL_OBSTACLES, range(15, 18), range(3, 7)),
        9: ('ice', ICE_FINALE_PATH_GRID, ICE_FINALE_OBSTACLES, range(7, 10), range(6, 9)),
    }
    if index not in special_maps:
        return dict(theme='cloud', path=PATH, path_cells=PATH_CELLS,
                    home_cells=HOME_CELLS,
                    obstacles=[(kind, col, row, 1, 1)
                               for (col, row), kind in OBSTACLES.items()]
                    + (CLOUD_OBSTACLES if index == 0 else []))
    theme, grid, obstacles, home_cols, home_rows = special_maps[index]
    grids = STRAIT_PATH_GRIDS if theme == 'strait' else (grid,)
    cells = set()
    for route in grids:
        for (ax, ay), (bx, by) in zip(route, route[1:]):
            cells.update((col, row) for col in range(min(ax, bx), max(ax, bx) + 1)
                         for row in range(min(ay, by), max(ay, by) + 1))
    routes = tuple([(GRID_X + (col + .5) * TILE, GRID_Y + (row + .5) * TILE)
                    for col, row in route] for route in grids)
    layout = dict(theme=theme, path=routes[0], routes=routes, path_cells=cells,
                  home_cells={(col, row) for col in home_cols for row in home_rows},
                  obstacles=obstacles)
    if theme == 'bay':
        layout['land_cells'] = {
            (pad % COLS, pad // COLS) for pad, (x, y) in enumerate(PADS)
            if all(on_bay_land(x + dx, y + dy) for dx in (-29, 29) for dy in (-29, 29))
        }
    return layout


def pad_at(position):
    col = int((position[0] - GRID_X) // TILE)
    row = int((position[1] - GRID_Y) // TILE)
    if 0 <= col < COLS and 0 <= row < ROWS:
        return row * COLS + col
    return None
TOWERS = {
    'bottle': dict(name='瓶子炮', subtitle='精准点射 · 单体攻击', cost=70,
                   damage=22, interval=.6, radius=155, color=(89, 215, 167)),
    'moon': dict(name='月亮', subtitle='月光领域 · 范围减速', cost=90,
                 damage=0, interval=1.50, radius=128, radius_step=8, color=(144, 206, 255),
                 slow_factor=.58, slow_duration=.8),
    'arrow': dict(name='弓箭', subtitle='穿云箭雨 · 范围伤害', cost=110,
                  damage=18, interval=1.15, radius=170, color=(186, 166, 255)),
    'star': dict(name='星星', subtitle='星芒冲击 · 单体溅射', cost=130,
                 damage=30, splash_damage=12, splash_radius=76,
                 interval=.95, radius=165, color=(255, 220, 100)),
    'sun': dict(name='太阳', subtitle='日冕脉冲 · 周身群伤', cost=140,
                damage=20, interval=1.05, radius=128, radius_step=8, color=(255, 176, 62)),
    'magic': dict(name='魔法球', subtitle='持续激光 · 单体锁定', cost=160,
                  damage=60, interval=1, radius=175, color=(187, 97, 255)),
    'fan': dict(name='风扇', subtitle='穿透叶片 · 伤害减速', cost=120,
                damage=16, interval=.95, radius=165, color=(57, 218, 139),
                slow_factor=.75, slow_duration=1.4, flight_distance=420, projectile_speed=340),
    'rocket': dict(name='火箭', subtitle='直线火箭 · 穿透伤害', cost=150,
                   damage=32, interval=1.20, radius=175, color=(250, 118, 74),
                   flight_distance=450, projectile_speed=430),
}
ENEMIES = {
    'crab': dict(hp=65, speed=56, reward=12, color=(255, 143, 125)),
    'jelly': dict(hp=45, speed=84, reward=11, color=(184, 153, 239)),
    'shell': dict(hp=180, speed=39, reward=22, color=(236, 181, 106)),
    'boss': dict(name='手柄大魔王', hp=1800, speed=32, reward=180,
                 hit_radius=46, leak_damage=10, color=(219, 119, 78)),
}
FOOD_ENEMIES = (
    ('soda_green', '清爽汽水布', 'jelly'),
    ('soda_orange', '橙味汽水布', 'jelly'),
    ('soda_red', '能量汽水布', 'jelly'),
    ('strawberry_cream', '草莓甜心布', 'crab'),
    ('beef_noodles', '红烧牛肉布', 'crab'),
    ('seafood_noodles', '鲜虾鱼板布', 'crab'),
    ('popcorn', '米花布', 'crab'),
    ('fries', '薯条布', 'jelly'),
    ('toast', '吐司布', 'crab'),
    ('burger', '美味布堡', 'shell'),
    ('swiss_roll', '瑞士卷布', 'shell'),
    ('cookie', '夹心布', 'shell'),
    ('potsticker', '煎饺布', 'crab'),
    ('steamed_bun', '包包布', 'crab'),
    ('mushroom', '菇菇布', 'shell'),
    ('yellow_pepper', '黄椒布', 'crab'),
)
FOOD_GROUPS = {
    template: [kind for kind, _, group in FOOD_ENEMIES if group == template]
    for template in ('crab', 'jelly', 'shell')
}
ENEMIES.update({kind: dict(ENEMIES[template], name=name)
                for kind, name, template in FOOD_ENEMIES})
DANGO_NAMES = ('花结团子', '蓝帽团子', '紫缎团子', '鹿冠团子', '金羽团子',
               '星坠团子', '粉翼团子', '琥珀团子', '冰角团子', '雪翎团子')
DANGO_KINDS = tuple(f'dango-{index}' for index in range(1, len(DANGO_NAMES) + 1))
ENEMIES.update({kind: dict(name=name, hp=90, speed=56, reward=14, hit_radius=28)
                for kind, name in zip(DANGO_KINDS, DANGO_NAMES)})
LEVEL_NAMES = ['云端初见', '冰糖雪原', '风语林地', '冰灯海湾', '双环冰港',
               '苔石溪谷', '雪帽冰原', '砂岩绿洲', '风车回廊', '冰阶决战']
CHARACTERS = {
    'whale': dict(name='大肥鱼', asset='whale-maid.png', price=0,
                  title='深蓝的陪伴'),
    'gpt': dict(name='GPT 娘', asset='gpt-girl.png', price=300,
                title='银白的星语'),
    'claude': dict(name='Claude 娘', asset='claude-girl.png', price=300,
                   title='暖橙的书页'),
}
INITIAL_STARS = sum(character['price'] for character in CHARACTERS.values())
FIRST_CLEAR_STARS = 100
REACTION_THRESHOLDS = (7, 3)


def portrait_key(character, lives):
    for threshold in reversed(REACTION_THRESHOLDS):
        if lives <= threshold:
            return f'{character}-{threshold}'
    return character


def level_config(index):
    waves = []
    next_food = dict.fromkeys(FOOD_GROUPS, index)
    for wave in range(5 + index // 2):
        count = 6 + wave * 2 + index
        interval = max(.36, 1.05 - wave * .07 - index * .03)
        if wave == 4:
            enemies = [DANGO_KINDS[index]] * count
            interval = .85
        else:
            groups = ['crab'] * count
            if wave >= 1:
                groups[1::3] = ['jelly'] * len(groups[1::3])
            if wave >= 2:
                groups[::5] = ['shell'] * len(groups[::5])
            enemies = []
            for group in groups:
                variants = FOOD_GROUPS[group]
                enemies.append(variants[next_food[group] % len(variants)])
                next_food[group] += 1
        waves.append(dict(enemies=enemies, interval=interval))
    if index == len(LEVEL_NAMES) - 1:
        waves[-1]['enemies'].append('boss')
    return dict(name=LEVEL_NAMES[index], coins=230 + index * 15, lives=10,
                hp_scale=1 + index * .16, waves=waves, layout=map_config(index))
