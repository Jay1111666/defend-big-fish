"""商店交易、首通奖励与真实磁盘存档的回归检查。"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import pygame
from config import CHARACTERS, INITIAL_STARS, FIRST_CLEAR_STARS
from progress import ProgressStore
from main import App


class ProgressTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='.test-progress-', dir=Path(__file__).resolve().parent)
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'progress.sqlite3'
        self.store = self.open_store()

    def open_store(self):
        store = ProgressStore(self.path)
        self.addCleanup(store.close)
        return store

    def test_initial_currency_buys_both_and_selection_survives_reopen(self):
        profile = self.store.snapshot()
        self.assertEqual(profile.selected, 'whale')
        self.assertEqual(profile.owned, {'whale'})
        self.assertEqual(profile.stars, sum(item['price'] for item in CHARACTERS.values()))
        self.assertFalse(self.store.select('gpt'))
        for key in ['gpt', 'claude']:
            self.assertEqual(self.store.purchase(key), 'purchased')
        self.assertEqual(self.store.purchase('gpt'), 'owned')
        self.assertEqual(self.store.snapshot().stars, 0)
        self.assertTrue(self.store.select('claude'))
        reopened = self.open_store().snapshot()
        self.assertEqual(reopened.stars, 0)
        self.assertEqual(reopened.selected, 'claude')
        self.assertEqual(reopened.owned, set(CHARACTERS))
        self.assertTrue(self.store.select('whale'))

    def test_first_clear_once_across_restarts(self):
        self.assertEqual(self.store.record_victory(0), FIRST_CLEAR_STARS)
        reopened = self.open_store()
        self.assertEqual(reopened.record_victory(0), 0)
        self.assertEqual(reopened.record_victory(9), FIRST_CLEAR_STARS)
        self.assertEqual(reopened.snapshot().stars, INITIAL_STARS + 2 * FIRST_CLEAR_STARS)
        self.assertEqual(reopened.snapshot().cleared, {0, 9})

    def test_insufficient_balance_and_unknown_character(self):
        with self.store.connection:
            self.store.connection.execute('UPDATE profile SET stars = 10')
        before = self.store.snapshot()
        self.assertEqual(self.store.purchase('gpt'), 'insufficient')
        self.assertEqual(self.store.purchase('unknown'), 'unknown')
        self.assertFalse(self.store.select('unknown'))
        self.assertEqual(before, self.store.snapshot())

    def test_failed_unlock_rolls_back_debit(self):
        self.store.connection.execute("CREATE TRIGGER fail_unlock BEFORE INSERT ON owned BEGIN SELECT RAISE(ABORT, 'disk failure'); END")
        with self.assertRaises(sqlite3.Error):
            self.store.purchase('gpt')
        self.assertEqual(self.store.snapshot().stars, INITIAL_STARS)
        self.assertNotIn('gpt', self.store.snapshot().owned)

    def test_failed_reward_rolls_back_clear_record_and_retries(self):
        self.store.connection.execute("CREATE TRIGGER fail_reward BEFORE UPDATE ON profile BEGIN SELECT RAISE(ABORT, 'disk failure'); END")
        with self.assertRaises(sqlite3.Error):
            self.store.record_victory(0)
        self.assertFalse(self.store.snapshot().cleared)
        self.store.connection.execute('DROP TRIGGER fail_reward')
        self.assertEqual(self.store.record_victory(0), FIRST_CLEAR_STARS)

    def test_two_windows_cannot_double_buy_or_claim(self):
        def transact(_):
            store = ProgressStore(self.path)
            try:
                return store.purchase('gpt'), store.record_victory(0)
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(transact, range(2)))
        self.assertEqual(sum(result[0] == 'purchased' for result in results), 1)
        self.assertEqual(sum(result[1] for result in results), FIRST_CLEAR_STARS)
        self.assertEqual(self.store.snapshot().stars, INITIAL_STARS - 300 + FIRST_CLEAR_STARS)

    def test_ui_buy_equip_pause_and_return(self):
        app = App(progress=self.store)
        self.addCleanup(pygame.quit)
        def click_action(action):
            app.draw()
            rect = next(rect for rect, name, enabled in app.buttons if name == action and enabled)
            app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
            app.draw()
        app.action('wave')
        app.advance(.1)
        before = app.game.enemies[0].position.copy()
        click_action('shop')
        app.advance(10)
        self.assertEqual(app.game.enemies[0].position, before)
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertEqual(app.game.waves.index, 0)
        click_action('buy:gpt')
        self.assertEqual(app.profile.stars, 300)
        self.assertEqual(app.profile.selected, 'whale')
        click_action('equip:gpt')
        self.assertEqual(app.profile.selected, 'gpt')
        click_action('buy:claude')
        click_action('equip:claude')
        self.assertEqual(app.profile.stars, 0)
        click_action('shop')
        app.advance(.1)
        self.assertNotEqual(app.game.enemies[0].position, before)
        app.reset(1)
        self.assertEqual(app.profile.selected, 'claude')
        self.assertEqual(self.open_store().snapshot().selected, 'claude')
        app.paused = True
        click_action('shop')
        click_action('shop')
        self.assertTrue(app.paused)

    def test_victory_normal_update_rewards_once_loss_never_rewards(self):
        app = App(progress=self.store)
        self.addCleanup(pygame.quit)
        app.game.waves.index = len(app.game.config['waves']) - 1
        app.game.waves.active = True
        app.advance(.01)
        self.assertEqual(app.game.state, 'won')
        self.assertEqual(app.profile.stars, INITIAL_STARS + FIRST_CLEAR_STARS)
        app.advance(1)
        app.settle_victory()
        self.assertEqual(app.profile.stars, INITIAL_STARS + FIRST_CLEAR_STARS)
        app.reset(0)
        app.game.waves.index = len(app.game.config['waves']) - 1
        app.game.waves.active = True
        app.advance(.01)
        self.assertEqual(app.profile.stars, INITIAL_STARS + FIRST_CLEAR_STARS)
        app.reset(1)
        app.game.lives = 0
        app.advance(.01)
        self.assertEqual(app.game.state, 'lost')
        self.assertNotIn(1, self.store.snapshot().cleared)

    def test_ui_failed_reward_can_retry_without_duplicate_credit(self):
        app = App(progress=self.store)
        self.addCleanup(pygame.quit)
        app.game.state = 'won'
        with patch.object(self.store, 'record_victory', side_effect=sqlite3.OperationalError('locked')):
            app.advance(0)
        self.assertFalse(app.reward_settled)
        app.draw()
        self.assertIn('reward', [action for _, action, _ in app.buttons])
        app.action('reward')
        app.action('reward')
        self.assertTrue(app.reward_settled)
        self.assertEqual(app.profile.stars, INITIAL_STARS + FIRST_CLEAR_STARS)


if __name__ == '__main__':
    unittest.main()
