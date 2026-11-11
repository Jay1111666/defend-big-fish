"""最终 Boss 与通关条件的回归检查。"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import unittest
from config import COLS, level_config, pad_at
from model import Game, Enemy, Tower


class BossTests(unittest.TestCase):
    def test_only_tenth_level_last_wave_has_one_boss(self):
        for level in range(10):
            waves = level_config(level)['waves']
            self.assertEqual(sum(w['enemies'].count('boss') for w in waves), int(level == 9))
            if level == 9:
                self.assertEqual(waves[-1]['enemies'][-1], 'boss')

    def final_wave(self):
        game = Game(9)
        game.waves.index = len(game.config['waves']) - 2
        game.waves.start()
        game.waves.queue = ['boss']
        game.update(0)
        return game

    def test_spawn_prevents_victory_until_death_and_rewards_once(self):
        game = self.final_wave()
        boss = game.boss
        self.assertIsNotNone(boss)
        self.assertEqual(boss.position, game.path[0])
        self.assertEqual(game.state, 'playing')
        self.assertEqual(game.boss_intro, 4)
        self.assertTrue(game.select_target_at(boss.position))
        coins = game.coins
        boss.take_damage(boss.hp)
        game.update(0)
        self.assertIsNone(game.priority_target)
        self.assertIsNone(game.boss)
        self.assertEqual(game.state, 'won')
        self.assertEqual(game.coins, coins + boss.reward)
        game.update(1)
        self.assertEqual(game.coins, coins + boss.reward)

    def test_boss_leak_is_defeat_even_in_final_wave(self):
        game = self.final_wave()
        boss = game.boss
        game.select_target_at(boss.position)
        boss.position.update(game.path[-1])
        boss.next_waypoint = len(game.path)
        game.update(.1)
        self.assertEqual(game.lives, 0)
        self.assertEqual(game.state, 'lost')
        self.assertIsNone(game.priority_target)
        self.assertEqual(game.kills, 0)

    def test_boss_can_be_slowed_and_takes_direct_and_splash_damage(self):
        boss, other = Enemy('boss'), Enemy('crab')
        boss.position.update(470, 352)
        other.position.update(480, 352)
        pad = pad_at((416, 352))
        Tower('moon', pad).update(0, [boss], [])
        boss.update(.5)
        self.assertAlmostEqual(boss.progress, 32 * .58 * .5)
        boss.position.update(470, 352)
        effects = []
        Tower('star', pad).update(0, [boss, other], effects, priority_target=other)
        effects[0].update(1, [boss, other], [], effects)
        self.assertEqual(boss.hp, boss.max_hp - 12)
        effects = []
        Tower('bottle', pad).update(0, [boss, other], effects, priority_target=boss)
        effects[0].update(1, [boss, other], [], effects)
        self.assertEqual(boss.hp, boss.max_hp - 34)

    def test_tenth_level_beatable_with_earned_coins(self):
        game = Game(9)
        plan = [('rocket', 15, 7), ('rocket', 14, 7), ('bottle', 13, 2),
                ('arrow', 13, 4), ('magic', 11, 5), ('sun', 5, 3),
                ('moon', 6, 3), ('magic', 8, 3)]
        boss = None
        for _ in range(90000):
            if len(game.towers) < len(plan):
                kind, col, row = plan[len(game.towers)]
                game.build(kind, row * COLS + col)
            else:
                for tower in game.towers:
                    game.upgrade(tower)
            if not game.waves.active:
                game.waves.start()
            game.update(1 / 60)
            boss = game.boss or boss
            if game.state != 'playing':
                break
        self.assertIsNotNone(boss)
        self.assertEqual(boss.status, 'dead')
        self.assertEqual(game.state, 'won')


if __name__ == '__main__':
    unittest.main()
