from pathlib import Path
import math
import random

import pygame

from game.audio.radio_lines import RADIO_LINES


RADIO_COOLDOWN_MS = 10000
RADIO_MAX_GAIN = .62 * .6


def radio_acoustics(camera, position):
    distance = pygame.Vector2(position).distance_to(camera.position)
    if distance >= 2000:
        return 0.0, 0.0
    zoom = max(0, min(1, (camera.zoom - .2) / 1.2))
    zoom = zoom * zoom * (3 - 2 * zoom)
    attenuation = (1 - (distance / 2000) ** 2) ** 2 / (1 + (distance / 520) ** 2)
    point = camera.world_to_screen(position)
    pan = max(-.7, min(.7, (point.x - camera.viewport_size[0] / 2) / (camera.viewport_size[0] * .75)))
    return RADIO_MAX_GAIN * (.2 + .8 * zoom) * attenuation, pan


class UnitRadio:
    def __init__(self):
        self.sounds = {}
        self.voices = {}
        self.channel = None
        self.active = True
        self.next_allowed_tick = 0
        self.last_phrase = None
        self.last_category = None
        self.last_action = None
        self.last_voice = None
        self.last_phrases = {}
        self.phrase_bags = {}
        self.randomizer = random.Random()
        self.speaker = None
        self.gain = RADIO_MAX_GAIN
        self.pan = 0
        if pygame.mixer.get_init() is None:
            return
        directory = Path(__file__).resolve().parents[1] / "assets" / "audio" / "radio"
        for category, actions in RADIO_LINES.items():
            for action, phrases in actions.items():
                sounds = {}
                voices = {}
                for phrase, voice in phrases.items():
                    path = directory / category / action / f"{phrase}.flac"
                    if path.is_file():
                        try:
                            sounds[phrase] = pygame.mixer.Sound(str(path))
                            voices[phrase] = voice
                        except (OSError, pygame.error):
                            continue
                if sounds:
                    self.sounds[category, action] = sounds
                    self.voices[category, action] = voices
        if self.sounds:
            pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
            pygame.mixer.set_reserved(5)
            self.channel = pygame.mixer.Channel(4)
            self.channel.set_volume(RADIO_MAX_GAIN, RADIO_MAX_GAIN)

    @property
    def playing(self):
        return self.channel is not None and pygame.mixer.get_init() is not None and self.channel.get_busy()

    def play(self, speaker=None, camera=None, category="infantry", action="select"):
        bank = category, action
        if not self.active or self.channel is None or pygame.mixer.get_init() is None or bank not in self.sounds:
            return False
        now = pygame.time.get_ticks()
        if self.playing or now < self.next_allowed_tick:
            return False
        gain, pan = radio_acoustics(camera, speaker.position) if camera is not None and speaker is not None else (RADIO_MAX_GAIN, 0)
        if gain < .001:
            return False
        bag = self.phrase_bags.setdefault(bank, [])
        if not bag:
            bag.extend(self.sounds[bank])
            self.randomizer.shuffle(bag)
        choices = [phrase for phrase in bag if phrase != self.last_phrases.get(bank)] or bag
        different_voices = [phrase for phrase in choices if self.voices[bank][phrase] != self.last_voice]
        phrase = (different_voices or choices)[-1]
        bag.remove(phrase)
        sound = self.sounds[bank][phrase]
        self.speaker = speaker
        self.gain, self.pan = gain, pan
        self.apply_volume()
        self.channel.play(sound)
        self.last_phrase = phrase
        self.last_category = category
        self.last_action = action
        self.last_voice = self.voices[bank][phrase]
        self.last_phrases[bank] = phrase
        self.next_allowed_tick = now + RADIO_COOLDOWN_MS
        return True

    def apply_volume(self):
        left = self.gain * math.sqrt((1 - self.pan) / 2)
        right = self.gain * math.sqrt((1 + self.pan) / 2)
        self.channel.set_volume(left, right)

    def update(self, active=True, camera=None, elapsed_seconds=0):
        if self.active and not active and self.playing:
            self.channel.fadeout(90)
        self.active = active
        if not active:
            return
        if active and self.playing and self.speaker is not None and camera is not None:
            gain, pan = radio_acoustics(camera, self.speaker.position)
            volume_blend = -math.expm1(-max(0, elapsed_seconds) / .12)
            pan_blend = -math.expm1(-max(0, elapsed_seconds) / .22)
            self.gain += (gain - self.gain) * volume_blend
            self.pan += (pan - self.pan) * pan_blend
            self.apply_volume()

    def close(self):
        if self.channel is not None and pygame.mixer.get_init() is not None:
            self.channel.stop()
        self.active = False
