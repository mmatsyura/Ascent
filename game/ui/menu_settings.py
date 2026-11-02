import json
import math

import pygame


class MenuSettings:
    def __init__(self, app):
        self.app = app
        self.path = app.profile.path.with_name("settings.json")
        self.music = 1.0
        self.effects = 1.0
        self.show_fps = True
        self.message = ""
        self.base_music = app.soundscape.music_level
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data.get("show_fps"), bool):
                self.show_fps = data["show_fps"]
            for key in ("music", "effects"):
                value = data.get(key, 1)
                if isinstance(value, (int, float)) and math.isfinite(value):
                    setattr(self, key, max(0, min(1, float(value))))
        except (OSError, ValueError, AttributeError):
            pass
        self.apply()

    def apply(self):
        self.app.soundscape.music_level = self.base_music * self.music
        if pygame.mixer.get_init() is None:
            return

        def volume(sounds):
            if isinstance(sounds, pygame.mixer.Sound):
                sounds.set_volume(self.effects)
            elif isinstance(sounds, dict):
                for sound in sounds.values():
                    volume(sound)
            elif isinstance(sounds, (list, tuple)):
                for sound in sounds:
                    volume(sound)

        for audio in (
            self.app.soundscape,
            self.app.mine_ambience,
            self.app.drone_ambience,
            self.app.unit_radio,
        ):
            volume(audio.sounds)
        for name in ("purchase_sound", "victory_sound", "explosion_sound", "notification_sound"):
            volume(getattr(self.app.soundscape, name, None))

    def set(self, key, value):
        setattr(self, key, max(0, min(1, value)))
        self.apply()

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(
                    {"music": self.music, "effects": self.effects, "show_fps": self.show_fps},
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary.replace(self.path)
            self.message = "Налаштування збережено"
        except OSError:
            self.message = "Не вдалося зберегти налаштування"
