from dataclasses import dataclass
from pathlib import Path
import math

import pygame


def create_mine_sounds():
    path = Path(__file__).resolve().parents[1] / "assets" / "audio" / "zavod.mp3"
    if not path.is_file():
        return ()
    return (pygame.mixer.Sound(str(path)),)


MINE_VOLUME_SCALE = 0.8 / 2.1 * 0.65


MINE_MAX_GAIN = 0.24 * MINE_VOLUME_SCALE


MINE_GROUP_RADIUS = 280


def mine_acoustics(camera, position):
    zoom = max(0, min(1, (camera.zoom - 0.35) / 1.4))
    zoom = zoom * zoom * (3 - 2 * zoom)
    distance = pygame.Vector2(position).distance_to(camera.position)
    if zoom <= 0 or distance >= 900:
        return 0.0, 0.0
    attenuation = (1 - (distance / 900) ** 2) ** 2 / (1 + (distance / 330) ** 2)
    point = camera.world_to_screen(position)
    width, height = camera.viewport_size
    edge = max(abs(point.x - width / 2) / (width / 2), abs(point.y - height / 2) / (height / 2))
    screen_gain = max(0, min(1, (1.4 - edge) / 0.4))
    pan = max(-1, min(1, (point.x - width / 2) / (width * 0.65)))
    return MINE_MAX_GAIN * zoom * attenuation * screen_gain, pan


def group_mines(candidates, active_mines):
    remaining = sorted(
        candidates,
        key=lambda item: item[0] * (1.12 if item[2] in active_mines else 1),
        reverse=True,
    )
    groups = []
    while remaining and len(groups) < 4:
        anchor = remaining[0][2]
        nearby = []
        distant = []
        for candidate in remaining:
            position = pygame.Vector2(candidate[2].position)
            if position.distance_squared_to(anchor.position) <= MINE_GROUP_RADIUS**2:
                nearby.append(candidate)
            else:
                distant.append(candidate)
        total = sum(gain for gain, _, _ in nearby)
        pan = sum(gain * pan for gain, pan, _ in nearby) / total
        groups.append((max(gain for gain, _, _ in nearby), pan, anchor))
        remaining = distant
    return groups


@dataclass
class MineVoice:
    mine: object
    channel: object
    gain: float = 0
    pan: float = 0
    drift_phase: float = 0


class MineAmbience:
    def __init__(self):
        self.voices = {}
        self.sounds = ()
        self.channels = ()
        self.elapsed_seconds = 0
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.sounds = create_mine_sounds()
            if self.sounds:
                pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
                pygame.mixer.set_reserved(4)
                self.channels = tuple(pygame.mixer.Channel(index) for index in range(4))
        except pygame.error:
            self.sounds = ()

    def update(self, buildings, camera, elapsed_seconds, active=True, volume_scale=1.0):
        if not self.sounds or pygame.mixer.get_init() is None:
            return
        elapsed_seconds = max(0, elapsed_seconds)
        if active:
            self.elapsed_seconds += elapsed_seconds
        candidates = []
        if active:
            for mine in buildings:
                if mine.owner == "blue" and mine.completed and mine.definition.key == "mine":
                    gain, pan = mine_acoustics(camera, mine.position)
                    gain *= max(0, min(1, volume_scale))
                    if gain > 0.0005:
                        candidates.append((gain, pan, mine))
        candidates = group_mines(candidates, self.voices)
        total = sum(gain for gain, _, _ in candidates)
        budget = max((gain for gain, _, _ in candidates), default=0)
        scale = budget / total if total else 1
        targets = {mine: (gain * scale, pan) for gain, pan, mine in candidates}
        volume_blend = -math.expm1(-elapsed_seconds / 0.35)
        pan_blend = -math.expm1(-elapsed_seconds / 0.65)
        for mine, voice in tuple(self.voices.items()):
            gain, pan = targets.get(mine, (0, voice.pan))
            drift = 0.22 * math.sin(self.elapsed_seconds * 0.4 + voice.drift_phase)
            pan += drift * (1 - abs(pan)) if gain else 0
            voice.gain += (gain - voice.gain) * volume_blend
            voice.pan += (pan - voice.pan) * pan_blend
            if gain == 0 and voice.gain < 0.0005:
                voice.channel.stop()
                del self.voices[mine]
        total_gain = sum(voice.gain for voice in self.voices.values())
        output_scale = min(1, MINE_MAX_GAIN / total_gain) if total_gain else 1
        for voice in self.voices.values():
            gain = voice.gain * output_scale
            left = gain * math.sqrt((1 - voice.pan) / 2)
            right = gain * math.sqrt((1 + voice.pan) / 2)
            voice.channel.set_volume(left, right)
        occupied = {voice.channel for voice in self.voices.values()}
        free = [channel for channel in self.channels if channel not in occupied]
        for _, pan, mine in candidates:
            if mine in self.voices or not free:
                continue
            channel = free.pop(0)
            channel.set_volume(0, 0)
            variant = (round(mine.position[0]) + round(mine.position[1])) % len(self.sounds)
            channel.play(self.sounds[variant], loops=-1)
            phase = (mine.position[0] * 0.017 + mine.position[1] * 0.029) % math.tau
            self.voices[mine] = MineVoice(mine, channel, pan=pan, drift_phase=phase)

    def close(self):
        if pygame.mixer.get_init() is not None:
            for voice in self.voices.values():
                voice.channel.stop()
        self.voices.clear()
