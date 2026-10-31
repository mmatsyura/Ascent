from dataclasses import dataclass
from pathlib import Path
import math

import pygame

from game.aircraft.definitions import TAKEOFF_DURATION


DRONE_MAX_GAIN = .035
MAX_DRONE_SOURCES = 4
DRONE_VOLUME = {"aviamen": 1.8}
DRONE_AUDIO_FILES = {
    "kamikaze": "dron_n1.flac",
    "p1_sun": "dron_n2.flac",
    "aviamen": "dron_n3.flac",
    "flamingo": "dron_n3.flac",
}


def drone_acoustics(camera, position):
    zoom = max(0, min(1, (camera.zoom - .25) / 1.35))
    zoom = zoom * zoom * (3 - 2 * zoom)
    distance = pygame.Vector2(position).distance_to(camera.position)
    if zoom <= 0 or distance >= 1100:
        return 0.0, 0.0
    attenuation = (1 - (distance / 1100) ** 2) ** 2 / (1 + (distance / 360) ** 2)
    point = camera.world_to_screen(position)
    width, height = camera.viewport_size
    edge = max(abs(point.x - width / 2) / (width / 2), abs(point.y - height / 2) / (height / 2))
    screen_gain = max(0, min(1, (1.35 - edge) / .35))
    pan = max(-1, min(1, (point.x - width / 2) / (width * .65)))
    return DRONE_MAX_GAIN * zoom * attenuation * screen_gain, pan


@dataclass
class DroneVoice:
    channel: object
    gain: float = 0
    pan: float = 0


class DroneAmbience:
    def __init__(self):
        self.sounds = {}
        self.channels = ()
        self.voices = {}
        if pygame.mixer.get_init() is None:
            return
        directory = Path(__file__).resolve().parents[1] / "assets" / "audio" / "drones"
        loaded = {}
        for key, filename in DRONE_AUDIO_FILES.items():
            path = directory / filename
            if path.is_file():
                try:
                    if filename not in loaded:
                        loaded[filename] = pygame.mixer.Sound(str(path))
                    self.sounds[key] = loaded[filename]
                except (OSError, pygame.error):
                    continue
        if self.sounds:
            pygame.mixer.set_num_channels(max(13, pygame.mixer.get_num_channels()))
            pygame.mixer.set_reserved(13)
            self.channels = tuple(pygame.mixer.Channel(index) for index in range(5, 13))

    def update(self, drones, camera, elapsed_seconds, active=True, volume_scale=1.0):
        if not self.sounds or pygame.mixer.get_init() is None:
            return
        candidates = []
        if active:
            level = max(0, min(1, volume_scale))
            for drone in drones:
                if drone.state not in ("takeoff", "cruising") or drone.definition.key not in self.sounds:
                    continue
                gain, pan = drone_acoustics(camera, drone.position)
                if drone.state == "takeoff":
                    progress = max(0, min(1, drone.state_time / TAKEOFF_DURATION))
                    gain *= .35 + .65 * progress * progress * (3 - 2 * progress)
                gain *= level * DRONE_VOLUME.get(drone.definition.key, 1.0)
                if gain > .00015:
                    candidates.append((gain, pan, drone))
        candidates.sort(key=lambda item: item[0] * (1.12 if item[2] in self.voices else 1), reverse=True)
        candidates = candidates[:MAX_DRONE_SOURCES]
        total = sum(gain for gain, _, _ in candidates)
        budget = max((gain for gain, _, _ in candidates), default=0)
        scale = budget / total if total else 1
        targets = {drone: (gain * scale, pan) for gain, pan, drone in candidates}
        elapsed_seconds = max(0, elapsed_seconds)
        volume_blend = -math.expm1(-elapsed_seconds / .28)
        pan_blend = -math.expm1(-elapsed_seconds / .25)
        for drone, voice in tuple(self.voices.items()):
            gain, pan = targets.get(drone, (0, voice.pan))
            voice.gain += (gain - voice.gain) * volume_blend
            voice.pan += (pan - voice.pan) * pan_blend
            if gain == 0 and voice.gain < .00015:
                voice.channel.stop()
                del self.voices[drone]
        total_gain = sum(voice.gain for voice in self.voices.values())
        output_scale = min(1, DRONE_MAX_GAIN * 1.8 / total_gain) if total_gain else 1
        for voice in self.voices.values():
            gain = voice.gain * output_scale
            left = gain * math.sqrt((1 - voice.pan) / 2)
            right = gain * math.sqrt((1 + voice.pan) / 2)
            voice.channel.set_volume(left, right)
        occupied = {voice.channel for voice in self.voices.values()}
        free = [channel for channel in self.channels if channel not in occupied]
        for _, pan, drone in candidates:
            if drone in self.voices or not free:
                continue
            channel = free.pop(0)
            channel.set_volume(0, 0)
            channel.play(self.sounds[drone.definition.key], loops=-1)
            self.voices[drone] = DroneVoice(channel, pan=pan)

    def close(self):
        if pygame.mixer.get_init() is not None:
            for voice in self.voices.values():
                voice.channel.stop()
        self.voices.clear()
