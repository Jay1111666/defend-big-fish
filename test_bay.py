"""回归检查冰灯海湾的占格规则与火箭的穿透伤害。"""
import unittest

from config import COLS, PADS, pad_at
from model import Enemy, Game, Obstacle, Tower


class BayTests(unittest.TestCase):
    def test_rocket_pierces_without_slowing_or_hitting_twice(self):
        tower = Tower('rocket', pad_at((416, 352)))
        primary, behind, beside = [Enemy('shell') for _ in range(3)]
        primary.position.update(490, 352)
        behind.position.update(610, 352)
        beside.position.update(610, 400)
        obstacle = Obstacle('rowboat', pad_at((672, 352)), 2, 1)
        enemies = [primary, behind, beside]
        effects = []
        tower.update(0, enemies, effects, [obstacle])
        self.assertEqual(len(effects), 1)
        rocket = effects[0]
        self.assertEqual(rocket.kind, 'rocket')
        primary.position.update(490, 400)
        rocket.update(.55, enemies, [obstacle], effects)
        rocket.update(.15, enemies, [obstacle], effects)
        self.assertEqual(rocket.position.y, 352)
        self.assertEqual(primary.hp, primary.max_hp)
        self.assertEqual(behind.hp, behind.max_hp - 32)
        self.assertEqual(beside.hp, beside.max_hp)
        self.assertEqual(obstacle.hp, obstacle.max_hp - 32)
        self.assertTrue(all(not enemy.slows for enemy in enemies))

    def test_moon_cooldown_exceeds_sun_at_each_level(self):
        pad = pad_at((416, 352))
        enemy = Enemy('shell')
        enemy.position.update(480, 352)
        for level in range(1, 4):
            moon, sun = Tower('moon', pad), Tower('sun', pad)
            moon.level = sun.level = level
            moon.update(0, [enemy], [])
            sun.update(0, [enemy], [])
            self.assertGreater(moon.cooldown, sun.cooldown)

    def test_bay_geometry_and_normal_clear(self):
        game = Game(3)
        land = game.layout['land_cells']
        blocked = set(game.layout['path_cells']) | game.layout['home_cells']
        self.assertTrue(game.layout['path_cells'] <= land)
        for obstacle in game.obstacles:
            cells = {(pad % COLS, pad // COLS) for pad in obstacle.cells}
            self.assertTrue(cells <= land)
            self.assertFalse(cells & blocked)
            self.assertTrue(all(not game.can_build(pad) for pad in obstacle.cells))
            blocked.update(cells)
        for pad in range(len(PADS)):
            self.assertEqual(game.can_build(pad), (pad % COLS, pad // COLS) in land - blocked)

        plan = [('rocket', 14, 3), ('bottle', 11, 4), ('moon', 13, 6),
                ('magic', 10, 5), ('sun', 8, 5)]
        for _ in range(60_000):
            if len(game.towers) < len(plan):
                kind, col, row = plan[len(game.towers)]
                game.build(kind, row * COLS + col)
            if not game.waves.active:
                game.waves.start()
            game.update(1 / 60)
            if game.state != 'playing':
                break
        self.assertEqual(game.state, 'won')
        self.assertEqual(game.lives, 10)
        self.assertEqual(game.towers[0].kind, 'rocket')
