"""浏览器存档契约与真实 App 输入、停战、音频解锁的检查。"""
import json
import os
import unittest
from unittest.mock import patch
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from browser_progress import BrowserProgressStore, MemoryStorage
from config import FIRST_CLEAR_STARS, INITIAL_STARS, PADS
from main import App
from progress import ProgressStore


class BrowserSaveTests(unittest.TestCase):
    def setUp(self):
        self.storage = MemoryStorage()
        self.store = BrowserProgressStore(self.storage)

    def test_reopen_preserves_purchases_selection_clears_and_audio(self):
        self.assertEqual(self.store.snapshot().stars, INITIAL_STARS)
        self.assertFalse(self.store.select('gpt'))
        self.assertEqual(self.store.purchase('gpt'), 'purchased')
        self.assertEqual(self.store.purchase('claude'), 'purchased')
        self.assertTrue(self.store.select('claude'))
        self.assertEqual(self.store.record_victory(9), FIRST_CLEAR_STARS)
        self.store.set_audio_setting('music', False)
        reopened = BrowserProgressStore(self.storage)
        self.assertEqual(reopened.snapshot().stars, FIRST_CLEAR_STARS)
        self.assertEqual(reopened.snapshot().selected, 'claude')
        self.assertEqual(reopened.snapshot().owned, {'whale', 'gpt', 'claude'})
        self.assertEqual(reopened.snapshot().cleared, {9})
        self.assertEqual(reopened.audio_settings(), {'music': False, 'effects': True})
        self.assertEqual(reopened.purchase('gpt'), 'owned')
        self.assertEqual(reopened.record_victory(9), 0)

    def test_write_failure_rolls_back_purchase_reward_and_setting(self):
        before = self.store.snapshot()
        for operation in (lambda: self.store.purchase('gpt'),
                          lambda: self.store.record_victory(0),
                          lambda: self.store.set_audio_setting('effects', False)):
            with self.subTest(operation=operation):
                with patch.object(self.storage, 'setItem', side_effect=RuntimeError('QuotaExceeded')):
                    with self.assertRaises(OSError):
                        operation()
                self.assertEqual(self.store.snapshot(), before)
                self.assertEqual(self.store.audio_settings(), {'music': True, 'effects': True})

    def test_corrupt_save_is_reported_without_overwriting_it(self):
        for raw in ('broken', '{}', json.dumps(dict(version=99)),
                    json.dumps(dict(BrowserProgressStore.initial(), stars=True)),
                    json.dumps(dict(BrowserProgressStore.initial(), selected='gpt'))):
            self.storage.setItem(self.store.KEY, raw)
            with self.assertRaises(OSError):
                BrowserProgressStore(self.storage)
            self.assertEqual(self.storage.getItem(self.store.KEY), raw)

    def test_same_origin_store_refreshes_and_avoids_repeated_sequential_claims(self):
        other = BrowserProgressStore(self.storage)
        self.store.purchase('gpt')
        self.assertEqual(other.purchase('gpt'), 'owned')
        self.store.record_victory(0)
        self.assertEqual(other.record_victory(0), 0)
        self.assertEqual(other.snapshot(), self.store.snapshot())

    def test_invalid_levels_and_unknown_characters(self):
        for level in (True, -1, 10, '0'):
            with self.assertRaises(ValueError):
                self.store.record_victory(level)
        self.assertEqual(self.store.purchase('unknown'), 'unknown')
        self.assertFalse(self.store.select('unknown'))

    def test_browser_and_desktop_store_follow_same_player_operations(self):
        desktop = ProgressStore(':memory:')
        self.addCleanup(desktop.close)
        for store in (self.store, desktop):
            store.purchase('gpt')
            store.select('gpt')
            store.record_victory(0)
            store.record_victory(0)
            store.set_audio_setting('effects', False)
        self.assertEqual(desktop.snapshot(), self.store.snapshot())
        self.assertEqual(desktop.audio_settings(), self.store.audio_settings())


class BrowserAppTests(unittest.TestCase):
    def setUp(self):
        self.store = BrowserProgressStore(MemoryStorage())
        self.app = App(progress=self.store, browser=True)
        self.addCleanup(pygame.quit)

    def test_start_screen_prevents_simulation_and_audio_until_clicked(self):
        self.app.draw()
        self.app.game.waves.start()
        self.app.advance(1)
        self.assertEqual(self.app.game.enemies, [])
        self.assertFalse(self.app.audio.unlocked)
        self.app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 435)))
        self.assertTrue(self.app.started)
        self.assertTrue(self.app.audio.unlocked)
        self.app.advance(.1)
        self.assertTrue(self.app.game.enemies)

    def test_touch_build_is_single_action_and_can_cancel_without_right_click(self):
        self.app.action('begin')
        self.app.draw()
        pad = next(p for p in range(len(PADS)) if self.app.game.can_build(p))
        x, y = PADS[pad]
        self.app.handle_event(pygame.event.Event(pygame.FINGERDOWN, x=x/1280, y=y/800))
        self.assertEqual(self.app.build_pad, pad)
        self.app.draw()
        rect = next(rect for rect, action, _ in self.app.buttons if action == 'bottle')
        self.app.handle_event(pygame.event.Event(pygame.FINGERDOWN, x=rect.centerx/1280, y=rect.centery/800))
        coins = self.app.game.coins
        self.app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center, touch=True))
        self.assertEqual(len(self.app.game.towers), 1)
        self.assertEqual(self.app.game.coins, coins)
        self.app.action('cancel')
        self.assertIsNone(self.app.selected)
        self.assertIsNone(self.app.game.priority_target)

    def test_focus_loss_pauses_wave_without_auto_resume(self):
        self.app.action('begin')
        self.app.action('wave')
        self.app.advance(.1)
        before = self.app.game.enemies[0].position.copy()
        self.app.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.app.advance(5)
        self.assertTrue(self.app.paused)
        self.assertEqual(self.app.game.enemies[0].position, before)
