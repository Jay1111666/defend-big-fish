"""持续光束、直线穿透、减速优先级与第三关。"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import unittest
import pygame
from config import COLS, ROWS, PADS, TOWERS, pad_at
from model import Game, Enemy, Tower, PiercingProjectile, Obstacle
from main import App
from progress import ProgressStore


class BeamTests(unittest.TestCase):
    def setUp(self):
        self.tower = Tower('magic', pad_at((416, 352)))
        self.a, self.b = Enemy('shell'), Enemy('shell')
        self.a.position.update(480, 352)
        self.b.position.update(500, 352)
        self.a.progress = 5
        self.enemies = [self.a, self.b]

    def test_continuous_damage_keeps_lock_when_other_enemy_overtakes(self):
        for frame in range(120):
            self.tower.update(1 / 120, self.enemies, [])
            self.b.progress += 1
            self.assertIs(self.tower.beam_target, self.a)
            self.assertTrue(self.tower.beam_active)
            self.assertAlmostEqual(self.a.hp, self.a.max_hp - (frame + 1) * .5)
        self.assertEqual(self.b.hp, self.b.max_hp)

    def test_death_range_exit_and_removal_release_beam(self):
        tower = self.tower
        tower.update(.1, [self.a], [])
        self.a.position.update(1000, 352)
        hp = self.a.hp
        tower.update(.1, [self.a], [])
        self.assertIsNone(tower.beam_target)
        self.assertEqual(self.a.hp, hp)
        tower.update(.1, self.enemies, [])
        self.assertIs(tower.beam_target, self.b)
        self.b.hp = 1
        tower.update(.1, self.enemies, [])
        self.assertEqual(self.b.status, 'dead')
        self.assertFalse(tower.beam_active)
        self.a.position.update(480, 352)
        tower.update(.1, [self.a], [])
        tower.update(.1, [], [])
        self.assertIsNone(tower.beam_target)

    def test_manual_retarget_and_frame_partition(self):
        self.tower.update(.5, self.enemies, [])
        self.tower.update(.5, self.enemies, [], priority_target=self.b)
        self.assertEqual(self.a.hp, 150)
        self.assertEqual(self.b.hp, 150)
        self.assertIs(self.tower.beam_target, self.b)
        enemy = Enemy('shell')
        enemy.position.update(self.a.position)
        other = Tower('magic', self.tower.pad)
        other.update(1, [enemy], [])
        self.assertEqual(enemy.hp, 120)


class SlowTests(unittest.TestCase):
    def test_moon_priority_even_when_fan_would_be_stronger_then_fan_resumes(self):
        enemy = Enemy('crab')
        enemy.apply_slow(.3, 1.4, 'fan')
        enemy.apply_slow(.58, .8, 'moon')
        self.assertEqual(enemy.slow_source, 'moon')
        enemy.update(.8)
        self.assertAlmostEqual(enemy.progress, 56 * .58 * .8)
        self.assertEqual(enemy.slow_source, 'fan')
        enemy.update(.6)
        self.assertIsNone(enemy.slow_source)
        self.assertAlmostEqual(enemy.progress, 56 * (.58 * .8 + .3 * .6))
        enemy.update(.5)
        self.assertAlmostEqual(enemy.progress, 56 * (.58 * .8 + .3 * .6 + .5))

    def test_fan_expires_during_moon_and_refresh_does_not_multiply(self):
        enemy = Enemy('crab')
        enemy.apply_slow(.75, .4, 'fan')
        enemy.apply_slow(.58, .8, 'moon')
        enemy.apply_slow(.58, .8, 'moon')
        self.assertEqual(len(enemy.slows), 2)
        enemy.update(1)
        self.assertAlmostEqual(enemy.progress, 56 * (.58 * .8 + .2))
        self.assertFalse(enemy.slows)

    def test_leaving_moon_range_expires_and_pulse_has_no_damage(self):
        moon = Tower('moon', pad_at((416, 352)))
        enemy = Enemy('shell')
        enemy.position.update(480, 352)
        effects = []
        moon.update(0, [enemy], effects)
        self.assertEqual(effects[0].kind, 'moon')
        self.assertEqual(effects[0].end, tuple(moon.position))
        enemy.position.update(900, 352)
        moon.update(.6, [enemy], effects)
        enemy.update(1)
        self.assertIsNone(enemy.slow_source)
        self.assertEqual(enemy.hp, enemy.max_hp)


class BladeTests(unittest.TestCase):
    def blade(self):
        return PiercingProjectile('fan', (100, 350), (300, 350), 16, 420, 340, (.75, 1.4))

    def test_swept_collision_pierces_overlaps_and_does_not_repeat_hits(self):
        enemies = [Enemy('shell') for _ in range(4)]
        for enemy, point in zip(enemies, [(200, 350), (200, 350), (400, 350), (300, 385)]):
            enemy.position.update(point)
        blade = self.blade()
        blade.update(1, enemies, [], [])
        self.assertEqual([e.hp for e in enemies], [164, 164, 164, 180])
        self.assertEqual([e.slow_source for e in enemies], ['fan', 'fan', 'fan', None])
        blade.update(.2, enemies, [], [])
        self.assertEqual([e.hp for e in enemies], [164, 164, 164, 180])
        blade.update(1, enemies, [], [])
        self.assertEqual(blade.life, 0)
        self.assertEqual(tuple(blade.position), (520, 350))

    def test_stays_straight_when_original_enemy_moves_or_dies(self):
        tower = Tower('fan', pad_at((416, 352)))
        enemy = Enemy('shell')
        enemy.position.update(500, 352)
        effects = []
        tower.update(0, [enemy], effects)
        blade = effects[0]
        enemy.position.update(500, 600)
        blade.update(.5, [enemy], [], effects)
        self.assertEqual(blade.position.y, 352)
        self.assertEqual(enemy.hp, enemy.max_hp)
        enemy.take_damage(9999)
        blade.update(.5, [enemy], [], effects)
        self.assertEqual(blade.position.y, 352)
        self.assertGreater(blade.position.x, 700)

    def test_obstacle_intersection_is_one_hit_for_entire_footprint(self):
        obstacle = Obstacle('windmill', 0, 2, 2)
        obstacle.position.update(300, 350)
        blade = self.blade()
        blade.update(1, [], [obstacle], [])
        blade.update(.5, [], [obstacle], [])
        self.assertEqual(obstacle.hp, obstacle.max_hp - 16)


class ForestTests(unittest.TestCase):
    def test_third_level_beatable_with_earned_coins_and_new_towers(self):
        game = Game(2)
        plan = [('fan', 2, 5), ('bottle', 4, 7), ('moon', 6, 5), ('magic', 8, 7),
                ('sun', 9, 3), ('star', 4, 2), ('magic', 13, 3), ('fan', 13, 5)]
        for _ in range(60000):
            if len(game.towers) < len(plan):
                kind, col, row = plan[len(game.towers)]
                game.build(kind, row * COLS + col)
            else:
                for tower in game.towers:
                    game.upgrade(tower)
            if not game.waves.active:
                game.waves.start()
            game.update(1 / 60)
            if game.state != 'playing':
                break
        self.assertEqual(game.state, 'won')
        self.assertEqual(game.lives, 10)

    def test_map_geometry_multi_cell_obstacles_and_enemy_route(self):
        game = Game(2)
        self.assertEqual(game.layout['theme'], 'forest')
        self.assertNotEqual(game.path, Game(0).path)
        self.assertNotEqual(game.path, Game(1).path)
        occupied = set()
        for obstacle in game.obstacles:
            for pad in obstacle.cells:
                self.assertTrue(0 <= pad < COLS * ROWS)
                self.assertNotIn(pad, occupied)
                self.assertNotIn((pad % COLS, pad // COLS), game.layout['path_cells'])
                self.assertNotIn((pad % COLS, pad // COLS), game.layout['home_cells'])
                self.assertFalse(game.can_build(pad))
            occupied.update(obstacle.cells)
        game.waves.start()
        game.update(0)
        enemy = game.enemies[0]
        enemy.update(1000)
        self.assertEqual(tuple(enemy.position), game.path[-1])

    def test_interface_fan_purchase_pause_beam_and_render_statuses(self):
        app = App(progress=ProgressStore(':memory:'))
        self.addCleanup(pygame.quit)
        self.addCleanup(app.progress.close)
        app.reset(2)
        pad = 5 * COLS + 2
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=PADS[pad]))
        app.draw()
        self.assertTrue(app.popup)
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_7))
        self.assertEqual(app.game.towers[0].kind, 'fan')
        self.assertEqual(app.game.coins, 260 - TOWERS['fan']['cost'])
        tower = Tower('magic', pad)
        enemy = Enemy('shell', path=app.game.path)
        enemy.position.update(tower.position + pygame.Vector2(60, 0))
        enemy.apply_slow(.75, 1.4, 'fan')
        app.game.enemies = [enemy]
        app.game.towers = [tower]
        app.advance(.1)
        hp = enemy.hp
        app.paused = True
        app.advance(.5)
        self.assertEqual(enemy.hp, hp)
        app.draw()
        enemy.apply_slow(.58, .8, 'moon')
        app.draw()
        self.assertEqual(enemy.slow_source, 'moon')
        app.reset(1)
        self.assertEqual(app.game.layout['theme'], 'ice')


if __name__ == '__main__':
    unittest.main()
