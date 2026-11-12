"""离线音乐、操作音效和受击声。"""
import pygame


class GameAudio:
    def __init__(self, directory, settings, deferred=False):
        self.settings = dict(settings)
        self.sounds = {}
        self.pending_hits = 0
        self.hit_channel = None
        self.hit_sounds = ()
        self.music_loaded = False
        self.unlocked = not deferred
        if pygame.mixer.get_init() is None:
            return

        for key in ('tap', 'build', 'hit', 'hit-ouch'):
            try:
                path = directory / f'{key}.ogg'
                sound = pygame.mixer.Sound(str(path if path.exists() else directory / f'{key}.wav'))
            except (pygame.error, OSError):
                continue
            sound.set_volume(.75 if key.startswith('hit') else .35)
            self.sounds[key] = sound
        self.hit_sounds = tuple(self.sounds[key] for key in ('hit', 'hit-ouch') if key in self.sounds)
        pygame.mixer.set_reserved(1)
        self.hit_channel = pygame.mixer.Channel(0)
        try:
            path = directory / 'garden-loop.ogg'
            pygame.mixer.music.load(str(path if path.exists() else directory / 'garden-loop.wav'))
            pygame.mixer.music.set_volume(.42)
            self.music_loaded = True
            self.set_enabled('music', self.settings['music'])
        except (pygame.error, OSError):
            self.music_loaded = False

    def set_enabled(self, key, enabled):
        self.settings[key] = enabled
        if key == 'music' and self.music_loaded and self.unlocked:
            if enabled:
                pygame.mixer.music.play(-1)
            else:
                pygame.mixer.music.stop()
        if key == 'effects' and not enabled:
            self.clear_hits()
            if self.hit_channel is not None:
                pygame.mixer.stop()

    def effect(self, key):
        if self.unlocked and self.settings['effects'] and key in self.sounds:
            self.sounds[key].play()

    def hit(self, count):
        if self.unlocked and count > 0 and self.settings['effects'] and self.hit_channel is not None and self.hit_sounds:
            self.pending_hits += count
            self.update()

    def update(self):
        if self.pending_hits and not self.hit_channel.get_busy():
            self.hit_channel.play(self.hit_sounds[0])
            if len(self.hit_sounds) == 2:
                self.hit_channel.queue(self.hit_sounds[1])
            self.pending_hits -= 1

    def clear_hits(self):
        self.pending_hits = 0
        if self.hit_channel is not None:
            self.hit_channel.stop()

    def unlock(self):
        if not self.unlocked:
            self.unlocked = True
            self.set_enabled('music', self.settings['music'])
