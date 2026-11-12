"""音频开关持久化、受击事件及立绘回归检查。"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from config import CHARACTERS, portrait_key
from main import App, pygame
from model import Enemy
from progress import ProgressStore
from game_audio import GameAudio
from art import ROOT


class AudioTests(unittest.TestCase):
    def test_browser_music_uses_native_backend_without_starting_sdl_music(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        backend = Mock()
        with patch.object(pygame.mixer.music, 'load') as load, patch.object(pygame.mixer.music, 'play') as play:
            audio = GameAudio(ROOT / 'assets' / 'audio', {'music': True, 'effects': True},
                              deferred=True, music_backend=backend)
            backend.setEnabled.assert_not_called()
            audio.unlock()
            audio.unlock()
            backend.setEnabled.assert_called_once_with(True)
            audio.set_enabled('effects', False)
            backend.setEnabled.assert_called_once_with(True)
            audio.set_enabled('music', False)
            audio.set_enabled('music', True)
            self.assertEqual([call.args for call in backend.setEnabled.call_args_list],
                             [(True,), (False,), (True,)])
            load.assert_not_called()
            play.assert_not_called()

    def test_audio_settings_are_independent_and_persist(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / 'save.sqlite3'
            store = ProgressStore(path)
            try:
                self.assertEqual(store.audio_settings(), {'music': True, 'effects': True})
                profile = store.snapshot()
                store.set_audio_setting('music', False)
            finally:
                store.close()
            reopened = ProgressStore(path)
            try:
                self.assertEqual(reopened.audio_settings(), {'music': False, 'effects': True})
                self.assertEqual(reopened.snapshot(), profile)
            finally:
                reopened.close()

    def test_all_characters_play_on_each_hit_and_use_health_poses(self):
        store = ProgressStore(':memory:')
        self.addCleanup(store.close)
        self.addCleanup(pygame.quit)
        app = App(progress=store)

        def leak(count):
            app.game.enemies.extend(Enemy('crab', path=[(0, 0), (0.5, 0)]) for _ in range(count))
            app.game.waves.active = True
            app.advance(.05)

        for key in CHARACTERS:
            store.purchase(key)
            store.select(key)
            app.profile = store.snapshot()
            app.reset(5)
            with patch.object(app.audio, 'hit') as hit:
                self.assertEqual(portrait_key(key, app.game.lives), key)
                leak(1)
                self.assertEqual(portrait_key(key, app.game.lives), key)
                hit.assert_called_once_with(1)
                leak(2)
                self.assertEqual(portrait_key(key, app.game.lives), f'{key}-7')
                leak(4)
                self.assertEqual(portrait_key(key, app.game.lives), f'{key}-3')
                leak(1)
                self.assertEqual([call.args for call in hit.call_args_list], [(1,), (2,), (4,), (1,)])
                app.advance(.05)
                self.assertEqual(hit.call_count, 4)

        app.reset(9)
        boss = Enemy('boss', path=[(0, 0), (0.25, 0)])
        app.game.enemies.append(boss)
        app.game.waves.active = True
        with patch.object(app.audio, 'hit') as hit:
            app.advance(.05)
            self.assertEqual(app.game.lives, 0)
            hit.assert_called_once_with(1)

    def test_settings_pause_combat_and_control_the_mixer(self):
        store = ProgressStore(':memory:')
        self.addCleanup(store.close)
        self.addCleanup(pygame.quit)
        app = App(progress=store)
        app.action('wave')
        app.action('settings')
        app.advance(.2)
        self.assertFalse(app.game.enemies)
        self.assertTrue(pygame.mixer.music.get_busy())
        app.action('audio:music')
        self.assertFalse(pygame.mixer.music.get_busy())
        app.audio.hit(1)
        channel = app.audio.hit_channel
        first, second = app.audio.sounds['hit'], app.audio.sounds['hit-ouch']
        self.assertIs(channel.get_sound(), first)
        self.assertIs(channel.get_queue(), second)
        self.assertEqual(app.audio.pending_hits, 0)
        deadline = pygame.time.get_ticks() + 2000
        while channel.get_sound() is first and pygame.time.get_ticks() < deadline:
            pygame.time.wait(5)
        self.assertIs(channel.get_sound(), second)
        app.audio.hit(1)
        self.assertIs(channel.get_sound(), second)
        self.assertEqual(app.audio.pending_hits, 1)
        channel.stop()
        app.audio.update()
        self.assertIs(channel.get_sound(), first)
        self.assertIs(channel.get_queue(), second)
        self.assertEqual(app.audio.pending_hits, 0)
        app.audio.hit(1)
        app.action('audio:effects')
        self.assertFalse(channel.get_busy())
        self.assertIsNone(channel.get_queue())
        self.assertEqual(app.audio.pending_hits, 0)
        app.audio.hit(1)
        self.assertFalse(channel.get_busy())
        app.action('settings')
        app.advance(.2)
        self.assertTrue(app.game.enemies)
