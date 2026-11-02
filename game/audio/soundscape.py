from pathlib import Path
import math

import numpy as np
import pygame


class Soundscape:
    def __init__(self):
        self.channel = None
        self.purchase_channel = None
        self.purchase_sound = None
        self.victory_sound = None
        self.explosion_channel = None
        self.explosion_sound = None
        self.next_explosion = 0
        self.notification_channel = None
        self.notification_sound = None
        self.next_notification = 0
        self.sounds = {}
        self.music_loaded = False
        self.music_level = 0.08
        self.gain = 0
        self.next_click = 0
        if pygame.mixer.get_init() is None:
            return
        pygame.mixer.set_num_channels(max(17, pygame.mixer.get_num_channels()))
        pygame.mixer.set_reserved(17)
        self.channel = pygame.mixer.Channel(13)
        self.purchase_channel = pygame.mixer.Channel(14)
        self.explosion_channel = pygame.mixer.Channel(15)
        self.notification_channel = pygame.mixer.Channel(16)
        rate, _, channels = pygame.mixer.get_init()
        self.create_explosion(rate, channels)
        duration = 3.4
        moments = np.arange(round(rate * duration)) / rate
        fanfare = np.zeros(len(moments))
        for start, frequency, length in (
            (0, 392, 0.5),
            (0.35, 493.88, 0.5),
            (0.7, 587.33, 0.6),
            (1.15, 783.99, 1.9),
        ):
            time = moments - start
            envelope = np.clip(time / 0.04, 0, 1) * np.clip((length - time) / 0.35, 0, 1)
            wave = np.sin(math.tau * frequency * time) + 0.25 * np.sin(
                math.tau * frequency * 2 * time
            )
            fanfare += wave * envelope * 0.07
        samples = np.rint(fanfare * 32767).astype(np.int16)
        if channels == 2:
            samples = np.repeat(samples[:, None], 2, axis=1)
        self.victory_sound = pygame.sndarray.make_sound(np.ascontiguousarray(samples))
        for key, frequency in (("click", 620), ("select", 460), ("order", 540)):
            time = np.arange(round(rate * 0.09)) / rate
            envelope = (1 - np.exp(-time * 850)) * np.exp(-time * 62)
            wave = np.sin(math.tau * frequency * time) + 0.28 * np.sin(
                math.tau * frequency * 1.5 * time
            )
            samples = np.rint(wave * envelope * 2400).astype(np.int16)
            if channels == 2:
                samples = np.repeat(samples[:, None], 2, axis=1)
            self.sounds[key] = pygame.sndarray.make_sound(np.ascontiguousarray(samples))
        directory = Path(__file__).resolve().parents[1] / "assets" / "audio"
        notification_file = directory / "notification.mp3"
        if notification_file.is_file():
            try:
                self.notification_sound = pygame.mixer.Sound(str(notification_file))
            except (OSError, pygame.error):
                pass
        purchase_file = directory / "buy.mp3"
        if purchase_file.is_file():
            try:
                self.purchase_sound = pygame.mixer.Sound(str(purchase_file))
            except (OSError, pygame.error):
                pass
        path = directory / "music" / "background_music.flac"
        if not path.is_file():
            path = directory / "background_music.mp3"
            self.music_level = 0.008
        if path.is_file():
            try:
                pygame.mixer.music.load(str(path))
                pygame.mixer.music.set_volume(0)
                pygame.mixer.music.play(-1)
                self.music_loaded = True
            except (OSError, pygame.error):
                pass

    def create_explosion(self, rate, channels):
        time = np.arange(round(rate * 1.35)) / rate
        noise = np.random.default_rng(56).uniform(-1, 1, len(time))
        rumble = np.convolve(noise, np.ones(23) / 23, mode="same")
        envelope = (1 - np.exp(-time * 220)) * np.exp(-time * 4.8)
        wave = (np.sin(math.tau * (63 * time - 15 * time * time)) * 0.23 + rumble * 2.1) * envelope
        wave += noise * np.exp(-time * 55) * 0.17
        wave *= np.clip((1.35 - time) / 0.15, 0, 1)
        samples = np.rint(np.clip(wave, -0.7, 0.7) * 32767).astype(np.int16)
        if channels == 2:
            samples = np.repeat(samples[:, None], 2, axis=1)
        self.explosion_sound = pygame.sndarray.make_sound(np.ascontiguousarray(samples))

    def explode(self, position, camera):
        if self.explosion_channel is None or pygame.mixer.get_init() is None:
            return
        now = pygame.time.get_ticks()
        if now < self.next_explosion:
            return
        distance = pygame.Vector2(position).distance_to(camera.position)
        gain = 0.25 * (0.3 + 0.7 * min(1, camera.zoom / 1.5)) / (1 + (distance / 650) ** 2)
        if gain < 0.002:
            return
        pan = max(
            -0.8,
            min(
                0.8,
                (camera.world_to_screen(position).x - camera.viewport_size[0] / 2)
                / camera.viewport_size[0],
            ),
        )
        self.explosion_channel.set_volume(
            gain * math.sqrt((1 - pan) / 2), gain * math.sqrt((1 + pan) / 2)
        )
        self.explosion_channel.play(self.explosion_sound)
        self.next_explosion = now + 180

    def information(self):
        if (
            self.notification_channel is None
            or self.notification_sound is None
            or pygame.mixer.get_init() is None
        ):
            return False
        now = pygame.time.get_ticks()
        if now < self.next_notification or self.notification_channel.get_busy():
            return False
        self.notification_channel.set_volume(0.14, 0.14)
        self.notification_channel.play(self.notification_sound)
        self.next_notification = now + round(self.notification_sound.get_length() * 1000) + 5000
        return True

    def click(self, kind="click"):
        if self.channel is None or pygame.mixer.get_init() is None:
            return
        now = pygame.time.get_ticks()
        if now < self.next_click:
            return
        self.next_click = now + 90
        self.channel.set_volume(0.35, 0.35)
        self.channel.play(self.sounds.get(kind, self.sounds["click"]))

    def purchase(self):
        if (
            self.purchase_sound is None
            or self.purchase_channel is None
            or pygame.mixer.get_init() is None
        ):
            return
        self.channel.stop()
        self.purchase_channel.set_volume(0.4, 0.4)
        self.purchase_channel.play(self.purchase_sound)

    def celebrate(self):
        if (
            self.victory_sound is not None
            and self.purchase_channel is not None
            and pygame.mixer.get_init() is not None
        ):
            self.purchase_channel.set_volume(0.4, 0.4)
            self.purchase_channel.play(self.victory_sound)

    def update(self, duration, focused=True, paused=False, speaking=False):
        if (
            not focused
            and self.purchase_channel is not None
            and pygame.mixer.get_init() is not None
        ):
            self.purchase_channel.fadeout(100)
            self.explosion_channel.fadeout(100)
            self.notification_channel.fadeout(100)
        if not self.music_loaded or pygame.mixer.get_init() is None:
            return
        target = self.music_level if focused else 0
        if paused:
            target *= 0.45
        if speaking:
            target *= 0.35
        self.gain += (target - self.gain) * -math.expm1(-max(0, duration) / 0.8)
        pygame.mixer.music.set_volume(self.gain)

    def close(self):
        if pygame.mixer.get_init() is not None:
            if self.channel is not None:
                self.channel.stop()
            if self.purchase_channel is not None:
                self.purchase_channel.stop()
            if self.explosion_channel is not None:
                self.explosion_channel.stop()
            if self.notification_channel is not None:
                self.notification_channel.stop()
            if self.music_loaded:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
