"""满级瓶子炮攻速光环：先写行为测试，再实现与重构。"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import unittest
import pygame
from config import TOWERS
from model import Game, Tower, Enemy, Obstacle, Projectile, PiercingProjectile
from main import App
from progress import ProgressStore


def tower(kind, x=300, y=300, level=1):
    result = Tower(kind, 0)
    result.position.update(x, y)
    result.level = level
    return result


def enemy(x=350, y=300):
    result = Enemy('boss', path=[(x, y), (10000, y)])
    result.speed = 0
    return result


class AuraTopologyTests(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.source = tower('bottle', level=3)
        self.target = tower('magic', 400)
        self.game.towers = [self.source, self.target]

    def test_only_level_three_bottle_provides_aura(self):
        for kind in TOWERS:
            for level in (1, 2, 3):
                with self.subTest(kind=kind, level=level):
                    self.source.kind, self.source.level = kind, level
                    expected = 1.25 if (kind, level) == ('bottle', 3) else 1
                    self.assertEqual(self.game.attack_speed_for(self.target), expected)

    def test_circle_boundary_and_diagonal_not_bounding_square(self):
        for dx, dy, expected in [(160, 0, 1.25), (160.001, 0, 1),
                                  (96, 128, 1.25), (120, 120, 1)]:
            with self.subTest(dx=dx, dy=dy):
                self.target.position.update(300 + dx, 300 + dy)
                self.assertEqual(self.game.attack_speed_for(self.target), expected)

    def test_all_tower_kinds_can_receive_aura(self):
        for kind in TOWERS:
            with self.subTest(kind=kind):
                self.target.kind = kind
                self.assertEqual(self.game.attack_speed_for(self.target), 1.25)

    def test_no_self_buff_but_two_bottles_can_support_each_other(self):
        self.assertEqual(self.game.attack_speed_for(self.source), 1)
        self.target.kind, self.target.level = 'bottle', 3
        self.assertEqual(self.game.attack_speed_for(self.source), 1.25)
        self.assertEqual(self.game.attack_speed_for(self.target), 1.25)

    def test_overlap_does_not_stack_and_survives_one_source_sale(self):
        other = tower('bottle', 380, level=3)
        self.game.towers.append(other)
        self.assertEqual(self.game.attack_speed_for(self.target), 1.25)
        self.game.sell(self.source)
        self.assertEqual(self.game.attack_speed_for(self.target), 1.25)
        self.game.sell(other)
        self.assertEqual(self.game.attack_speed_for(self.target), 1)

    def test_upgrade_and_sale_apply_immediately_without_resetting_cooldown(self):
        self.source.level = 2
        self.game.coins = 1000
        self.target.cooldown = .3
        self.assertEqual(self.game.attack_speed_for(self.target), 1)
        self.assertTrue(self.game.upgrade(self.source))
        self.assertEqual(self.game.attack_speed_for(self.target), 1.25)
        self.assertEqual(self.target.cooldown, .3)
        self.game.sell(self.source)
        self.assertEqual(self.game.attack_speed_for(self.target), 1)
        self.assertEqual(self.target.cooldown, .3)

    def test_failed_upgrade_and_removed_recipient_never_get_buff(self):
        self.source.level = 2
        self.game.coins = 0
        self.assertFalse(self.game.upgrade(self.source))
        self.assertEqual(self.game.attack_speed_for(self.target), 1)
        self.source.level = 3
        self.game.sell(self.target)
        self.assertEqual(self.game.attack_speed_for(self.target), 1)

    def test_reset_does_not_retain_old_sources(self):
        replacement = Game()
        replacement.towers = [self.target]
        self.assertEqual(replacement.attack_speed_for(self.target), 1)


class AuraAttackTests(unittest.TestCase):
    def test_every_periodic_tower_fires_at_shorter_interval_for_all_levels(self):
        for kind in TOWERS:
            if kind == 'magic':
                continue
            for level in (1, 2, 3):
                with self.subTest(kind=kind, level=level):
                    subject, victim, effects = tower(kind, level=level), enemy(), []
                    subject.update(0, [victim], effects, attack_speed=1.25)
                    self.assertEqual(len(effects), 1)
                    interval = TOWERS[kind]['interval'] / (1 + .1 * (level - 1)) / 1.25
                    subject.update(interval - .0001, [victim], effects, attack_speed=1.25)
                    self.assertEqual(len(effects), 1)
                    subject.update(.0002, [victim], effects, attack_speed=1.25)
                    self.assertEqual(len(effects), 2)

    def test_buff_added_and_removed_mid_cooldown_preserves_completed_work(self):
        subject, victim, effects = tower('bottle'), enemy(), []
        subject.update(0, [victim], effects)
        subject.update(.2, [victim], effects)  # .4 秒基础冷却剩余
        subject.update(.16, [victim], effects, attack_speed=1.25)  # 完成 .2 秒
        subject.update(.1999, [victim], effects)  # 移除光环，不重置也不瞬发
        self.assertEqual(len(effects), 1)
        subject.update(.0002, [victim], effects)
        self.assertEqual(len(effects), 2)

    def test_idle_time_does_not_bank_a_burst(self):
        subject, effects = tower('rocket'), []
        subject.update(30, [], effects, attack_speed=1.25)
        subject.update(0, [enemy()], effects, attack_speed=1.25)
        self.assertEqual(len(effects), 1)
        subject.update(.01, [enemy()], effects, attack_speed=1.25)
        self.assertEqual(len(effects), 1)

    def test_beam_damage_scales_with_level_and_real_elapsed_time(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                subject, victim = tower('magic', level=level), enemy()
                subject.update(.4, [victim], [], attack_speed=1.25)
                expected = 60 * (1 + .65 * (level - 1)) * .4 * 1.25
                self.assertAlmostEqual(victim.max_hp - victim.hp, expected)
                self.assertIs(subject.beam_target, victim)
                self.assertTrue(subject.beam_active)

    def test_beam_dynamic_buff_and_frame_partition_keep_same_damage(self):
        losses = []
        for steps in (1, 100):
            subject, victim = tower('magic'), enemy()
            for dt, rate in [(.6, 1.25), (.4, 1)]:
                for _ in range(steps):
                    subject.update(dt / steps, [victim], [], attack_speed=rate)
            losses.append(victim.max_hp - victim.hp)
        for loss in losses:
            self.assertAlmostEqual(loss, 69)

    def test_beam_keeps_lock_and_stops_outside_range_or_on_death(self):
        subject, a, b = tower('magic'), enemy(), enemy(360)
        subject.update(.1, [a], [], attack_speed=1.25)
        b.progress = 999
        subject.update(.1, [a, b], [], attack_speed=1.25)
        self.assertIs(subject.beam_target, a)
        a.position.x = 1000
        before = a.hp
        subject.update(.1, [a], [], attack_speed=1.25)
        self.assertEqual(a.hp, before)
        self.assertFalse(subject.beam_active)
        b.hp = 1
        subject.update(.1, [b], [], attack_speed=1.25)
        self.assertEqual(b.status, 'dead')
        self.assertIsNone(subject.beam_target)

    def test_beam_manual_obstacle_target_also_gets_dps_bonus(self):
        subject, obstacle = tower('magic'), Obstacle('trees', 0)
        obstacle.position.update(350, 300)
        subject.update(.4, [], [], [obstacle], obstacle, attack_speed=1.25)
        self.assertAlmostEqual(obstacle.max_hp - obstacle.hp, 30)

    def test_projectile_damage_speed_distance_and_slow_are_not_multiplied(self):
        for kind in ('bottle', 'star', 'fan', 'rocket'):
            with self.subTest(kind=kind):
                shots = []
                for rate in (1, 1.25):
                    effects = []
                    tower(kind).update(0, [enemy()], effects, attack_speed=rate)
                    shots.append(effects[0])
                a, b = shots
                for field in ('damage', 'speed', 'life'):
                    self.assertEqual(getattr(a, field), getattr(b, field))
                if isinstance(a, PiercingProjectile):
                    self.assertEqual(a.slow, b.slow)
                    self.assertEqual(a.remaining_distance, b.remaining_distance)
                else:
                    self.assertIsInstance(a, Projectile)
                    self.assertEqual(a.splash_damage, b.splash_damage)
                a.update(.05, [], [], [])
                b.update(.05, [], [], [])
                self.assertEqual(a.position, b.position)

    def test_piercing_projectile_hits_each_instance_once_even_when_buffed(self):
        for kind in ('fan', 'rocket'):
            with self.subTest(kind=kind):
                victim, effects = enemy(380), []
                tower(kind).update(0, [victim], effects, attack_speed=1.25)
                shot = effects[0]
                for _ in range(20):
                    shot.update(.02, [victim], [], [])
                self.assertEqual(victim.max_hp - victim.hp, TOWERS[kind]['damage'])

    def test_aoe_damage_radius_and_moon_slow_duration_stay_unchanged(self):
        for kind in ('sun', 'moon', 'arrow'):
            with self.subTest(kind=kind):
                results = []
                for rate in (1, 1.25):
                    victims, effects = [enemy(350), enemy(360)], []
                    tower(kind).update(0, victims, effects, attack_speed=rate)
                    results.append(([e.hp for e in victims], effects[0].radius,
                                    [(e.active_slow.multiplier, e.active_slow.remaining)
                                     for e in victims if e.active_slow]))
                self.assertEqual(results[0], results[1])
                if kind == 'moon':
                    self.assertEqual(results[1][2], [(.58, .8), (.58, .8)])

    def test_sun_has_no_delayed_burn_damage(self):
        subject, victim = tower('sun'), enemy()
        subject.update(0, [victim], [])
        after = victim.hp
        victim.update(5)
        self.assertEqual(victim.hp, after)
        self.assertFalse(hasattr(victim, 'burns'))


class AuraIntegrationTests(unittest.TestCase):
    def test_game_applies_aura_before_attacks_independent_of_list_order(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                game = Game()
                source, target, victim = tower('bottle', level=3), tower('magic', 400), enemy(450)
                source.cooldown = 99
                game.towers = [source, target][:: -1 if reverse else 1]
                game.enemies, game.obstacles = [victim], []
                game.waves.active = True
                game.update(.4)
                self.assertAlmostEqual(victim.max_hp - victim.hp, 30)

    def test_preparation_pause_and_intermission_freeze_buffed_attacks(self):
        app = App(progress=ProgressStore(':memory:'))
        self.addCleanup(app.progress.close)
        self.addCleanup(pygame.quit)
        source, target, victim = tower('bottle', level=3), tower('magic', 400), enemy(450)
        source.cooldown = 99
        app.game.towers, app.game.enemies = [source, target], [victim]
        app.game.obstacles = []
        app.advance(2)
        self.assertEqual(victim.hp, victim.max_hp)
        app.action('wave')
        app.advance(.2)
        self.assertAlmostEqual(victim.max_hp - victim.hp, 15)
        app.action('pause')
        app.advance(2)
        self.assertAlmostEqual(victim.max_hp - victim.hp, 15)
        app.action('pause')
        app.advance(.2)
        self.assertAlmostEqual(victim.max_hp - victim.hp, 30)
        app.game.waves.active = False
        before = source.cooldown
        app.advance(2)
        self.assertAlmostEqual(victim.max_hp - victim.hp, 30)
        self.assertEqual(source.cooldown, before)

    def test_buffed_beam_kill_rewards_once_clears_lock_and_wins(self):
        game = Game()
        source, target, victim = tower('bottle', level=3), tower('magic', 400), enemy(450)
        source.cooldown = 99
        victim.hp = 7
        game.towers, game.enemies, game.obstacles = [source, target], [victim], []
        game.priority_target = victim
        game.waves.active = True
        game.waves.index = len(game.config['waves']) - 1
        coins = game.coins
        game.update(.1)
        self.assertEqual(game.state, 'won')
        self.assertIsNone(game.priority_target)
        self.assertEqual(game.coins, coins + victim.reward)
        game.update(10)
        self.assertEqual(game.coins, coins + victim.reward)
        self.assertEqual(game.kills, 1)


if __name__ == '__main__':
    unittest.main()
