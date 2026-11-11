"""双入口和旋转炮头的回归检查。"""
import unittest

from config import COLS, pad_at
from model import Enemy, Game, Tower


class StraitTests(unittest.TestCase):
    def test_both_entrances_spawn_and_reach_the_same_home(self):
        game = Game(4)
        left, right = game.layout['routes']
        self.assertNotEqual(left[0], right[0])
        self.assertEqual(left[-1], right[-1])
        game.waves.start()
        game.waves.update(0, game.enemies)
        game.waves.update(game.config['waves'][0]['interval'], game.enemies)
        self.assertEqual([enemy.path for enemy in game.enemies], [left, right])
        for route in (left, right):
            for x, y in route:
                self.assertFalse(game.can_build(pad_at((x, y))))
        blocked = game.layout['path_cells'] | game.layout['home_cells']
        occupied = set()
        for obstacle in game.obstacles:
            cells = {(pad % COLS, pad // COLS) for pad in obstacle.cells}
            self.assertFalse(cells & (blocked | occupied))
            occupied.update(cells)
        for enemy in game.enemies:
            enemy.update(1_000)
            self.assertEqual(enemy.position, left[-1])

    def test_weapons_track_on_cooldown_without_firing_again(self):
        for kind in Tower.AIMED_KINDS:
            with self.subTest(kind=kind):
                tower = Tower(kind, pad_at((416, 352)))
                target = Enemy('shell')
                target.position.update(512, 352)
                effects = []
                tower.update(0, [target], effects)
                self.assertAlmostEqual(tower.aim_angle, 0)
                self.assertAlmostEqual(effects[0].position.x if hasattr(effects[0], 'position')
                                       else effects[0].start[0], 437)
                target.position.update(416, 448)
                tower.update(.05, [target], effects)
                self.assertAlmostEqual(tower.aim_angle, 45)
                self.assertGreater(tower.recoil, 0)
                tower.update(.1, [target], effects)
                self.assertAlmostEqual(tower.aim_angle, 90)
                self.assertEqual(tower.recoil, 0)
                self.assertEqual(len(effects), 1)
