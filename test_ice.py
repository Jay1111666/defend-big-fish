"""冰雪地图、多格障碍、新炮塔与飞行弹丸。"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import unittest
import pygame
from config import COLS, ROWS, PADS, PATH, TOWERS, WIDTH, HEIGHT, pad_at
from model import Game, Enemy, Tower, Obstacle, Projectile
from main import App
from progress import ProgressStore


class IceMapTests(unittest.TestCase):
    def test_independent_route_and_no_overlapping_obstacles(self):
        game = Game(1)
        self.assertNotEqual(game.path, PATH)
        self.assertEqual(Game(0).path, PATH)
        self.assertEqual(len(game.obstacles), 27)
        occupied = set()
        for obstacle in game.obstacles:
            for cell in obstacle.cells:
                self.assertTrue(0 <= cell < COLS * ROWS)
                self.assertNotIn(cell, occupied)
                self.assertNotIn((cell % COLS, cell // COLS), game.layout['path_cells'])
                self.assertNotIn((cell % COLS, cell // COLS), game.layout['home_cells'])
                self.assertFalse(game.can_build(cell))
            occupied.update(obstacle.cells)
        for a, b in zip(game.path, game.path[1:]):
            self.assertTrue(a[0] == b[0] or a[1] == b[1])
        game.waves.start()
        game.update(0)
        enemy = game.enemies[0]
        self.assertEqual(tuple(enemy.position), game.path[0])
        enemy.update(1000)
        self.assertEqual(tuple(enemy.position), game.path[-1])
        self.assertEqual(enemy.status, 'escaped')

    def test_large_obstacle_select_any_cell_reward_once_and_release_all(self):
        for kind in ['igloo', 'iceberg', 'snowtrees']:
            with self.subTest(kind=kind):
                game = Game(1)
                obstacle = next(o for o in game.obstacles if o.kind == kind)
                for pad in obstacle.cells:
                    self.assertTrue(game.select_target_at(PADS[pad]))
                    self.assertIs(game.priority_target, obstacle)
                coins = game.coins
                obstacle.take_damage(9999)
                game.update(0)
                self.assertEqual(game.coins, coins + obstacle.reward)
                self.assertIsNone(game.priority_target)
                for pad in obstacle.cells:
                    self.assertTrue(game.can_build(pad))
                game.update(0)
                self.assertEqual(game.coins, coins + obstacle.reward)
                self.assertFalse(Game(1).can_build(obstacle.pad))

    def test_level_two_beatable_with_normal_income(self):
        game = Game(1)
        self.assertFalse(game.towers)
        plan = [('bottle', 1, 5), ('sun', 3, 6), ('magic', 5, 5), ('star', 7, 5),
                ('moon', 9, 5), ('magic', 13, 3), ('sun', 13, 6), ('bottle', 13, 4)]
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
        self.assertLess(len(game.obstacles), 27)


class NewAttackTests(unittest.TestCase):
    def test_moon_and_sun_upgrades_expand_hit_and_effect_radius_together(self):
        for kind in ('moon', 'sun'):
            with self.subTest(tower=kind):
                game = Game()
                game.coins = 1000
                self.assertTrue(game.build(kind, pad_at((416, 352))))
                tower = game.towers[0]
                for level, radius in enumerate((128, 136, 144), 1):
                    if level > 1:
                        self.assertTrue(game.upgrade(tower))
                    self.assertEqual(tower.radius, radius)
                    inside, outside = Enemy('shell'), Enemy('shell')
                    inside.position = tower.position + (radius, 0)
                    outside.position = tower.position + (radius + 1, 0)
                    tower.cooldown = 0
                    effects = []
                    tower.update(0, [inside, outside], effects)
                    self.assertEqual([effect.radius for effect in effects], [radius])
                    if kind == 'moon':
                        self.assertEqual(inside.slow_source, 'moon')
                        self.assertIsNone(outside.slow_source)
                    else:
                        self.assertLess(inside.hp, inside.max_hp)
                        self.assertEqual(outside.hp, outside.max_hp)
                self.assertFalse(game.upgrade(tower))

    def test_sun_hits_each_victim_once_including_large_obstacle_edge(self):
        sun = Tower('sun', pad_at((416, 352)))
        inside, outside = Enemy('shell'), Enemy('shell')
        inside.position = sun.position + (sun.radius, 0)
        outside.position = sun.position + (sun.radius + 1, 0)
        big = Obstacle('igloo', 0, 2, 2)
        big.position.update(600, 352)  # 中心不在范围内，左边缘在范围内。
        effects = []
        sun.update(0, [inside, outside], effects, [big])
        self.assertEqual(inside.hp, inside.max_hp - 20)
        self.assertEqual(outside.hp, outside.max_hp)
        self.assertEqual(big.hp, big.max_hp - 20)
        self.assertEqual(effects[0].end, tuple(sun.position))
        self.assertEqual(effects[0].radius, sun.radius)
        sun.cooldown = 0
        sun.update(0, [], effects, [big])
        self.assertEqual(big.hp, big.max_hp - 40)

    def test_magic_hits_only_marked_instance_and_can_destroy_obstacle(self):
        tower = Tower('magic', pad_at((416, 352)))
        first, second = Enemy('shell'), Enemy('shell')
        first.position.update(480, 352)
        second.position.update(first.position)
        effects = []
        tower.update(1, [first, second], effects, priority_target=second)
        self.assertEqual(first.hp, first.max_hp)
        self.assertEqual(second.hp, second.max_hp - 60)
        self.assertIs(tower.beam_target, second)
        self.assertTrue(tower.beam_active)
        obstacle = Obstacle('icecrystal', 0)
        obstacle.position.update(first.position)
        obstacle.hp = 60
        tower.cooldown = 0
        tower.update(1, [first, second], effects, [obstacle], obstacle)
        self.assertEqual(obstacle.status, 'dead')
        self.assertEqual(first.hp, first.max_hp)

    def test_bean_has_flight_time_tracks_original_target_and_hits_once(self):
        tower = Tower('bottle', pad_at((416, 352)))
        target = Enemy('shell')
        target.position.update(550, 352)
        effects = []
        tower.update(0, [target], effects)
        self.assertEqual(target.hp, target.max_hp)
        shot = effects[0]
        self.assertIsInstance(shot, Projectile)
        shot.update(.1, [target], [], effects)
        self.assertGreater(shot.position.x, tower.position.x)
        self.assertLess(shot.position.x, target.position.x)
        self.assertEqual(target.hp, target.max_hp)
        target.position.update(570, 360)
        shot.update(.5, [target], [], effects)
        self.assertEqual(tuple(shot.position), tuple(target.position))
        self.assertEqual(target.hp, target.max_hp - 22)
        shot.update(.5, [target], [], effects)
        self.assertEqual(target.hp, target.max_hp - 22)

    def test_star_impact_uses_moving_target_center_and_no_lock_transfer(self):
        primary, old_neighbour, new_neighbour = [Enemy('shell') for _ in range(3)]
        primary.position.update(550, 352)
        old_neighbour.position.update(500, 352)
        new_neighbour.position.update(640, 352)
        shot = Projectile('star', (416, 352), primary, 30, 76, 12)
        effects = []
        primary.position.update(620, 352)
        shot.update(1, [primary, old_neighbour, new_neighbour], [], effects)
        self.assertEqual(primary.hp, primary.max_hp - 30)
        self.assertEqual(old_neighbour.hp, old_neighbour.max_hp)
        self.assertEqual(new_neighbour.hp, new_neighbour.max_hp - 12)
        self.assertEqual(effects[0].end, (620, 352))
        shot = Projectile('bottle', (416, 352), primary, 22)
        primary.take_damage(9999)
        new_neighbour.position.update(primary.position)
        hp = new_neighbour.hp
        shot.update(1, [new_neighbour], [], effects)
        self.assertEqual(new_neighbour.hp, hp)

    def test_star_still_splashes_if_primary_dies_in_flight(self):
        primary, neighbour = Enemy('crab'), Enemy('shell')
        primary.position.update(550, 352)
        neighbour.position.update(primary.position)
        shot = Projectile('star', (416, 352), primary, 30, 76, 12)
        primary.take_damage(9999)
        effects = []
        shot.update(1, [neighbour], [], effects)
        self.assertEqual(neighbour.hp, neighbour.max_hp - 12)
        self.assertEqual(effects[0].end, (550, 352))


class IceInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.app = App(progress=ProgressStore(':memory:'))
        self.app.reset(1)

    def tearDown(self):
        self.app.progress.close()
        pygame.quit()

    def test_window_only_and_switching_maps_changes_rendered_route(self):
        app = self.app
        app.draw()
        self.assertFalse(any(action == 'fullscreen' for _, action, _ in app.buttons))
        for key, mod in [(pygame.K_F11, 0), (pygame.K_RETURN, pygame.KMOD_ALT)]:
            app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod))
            self.assertFalse(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN)
            self.assertEqual(app.screen.get_size(), (WIDTH, HEIGHT))
        ice_map = app.art.map
        app.reset(0)
        self.assertIsNot(app.art.map, ice_map)
        app.reset(1)
        self.assertIs(app.art.map, ice_map)
        app.reset(9)
        self.assertIsNot(app.art.map, ice_map)
        app.reset(2)
        forest_map = app.art.map
        app.reset(8)
        self.assertIsNot(app.art.map, forest_map)
        app.reset(1)
        self.assertIs(app.art.map, ice_map)

    def test_eight_card_menu_fits_every_free_cell_and_new_tower_purchases(self):
        app = self.app
        for pad in range(len(PADS)):
            if app.game.can_build(pad):
                app.build_pad = pad
                app.draw()
                self.assertTrue(pygame.Rect(0, 100, WIDTH, 620).contains(app.popup))
                self.assertEqual(len([action for _, action, _ in app.buttons if action in TOWERS]), 8)
        for kind in ['sun', 'magic', 'fan', 'rocket']:
            app.reset(1)
            pad = 5 * COLS + 1
            app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=PADS[pad]))
            app.draw()
            rect = next(rect for rect, action, _ in app.buttons if action == kind)
            app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
            self.assertEqual(app.game.towers[0].kind, kind)
            self.assertEqual(app.game.coins, 245 - TOWERS[kind]['cost'])

    def test_pause_and_shop_freeze_projectiles(self):
        app = self.app
        enemy = Enemy('shell', path=app.game.path)
        enemy.position.update(300, 400)
        shot = Projectile('star', (200, 400), enemy, 30, 76, 12)
        app.game.enemies = [enemy]
        app.game.effects = [shot]
        app.game.waves.active = True
        app.paused = True
        app.advance(.5)
        self.assertEqual(tuple(shot.position), (200, 400))
        app.paused = False
        app.action('shop')
        app.advance(.5)
        self.assertEqual(tuple(shot.position), (200, 400))
        app.action('shop')
        app.advance(.1)
        self.assertNotEqual(tuple(shot.position), (200, 400))


if __name__ == '__main__':
    unittest.main()
