import json
import os
from pathlib import Path


class PlayerProfile:
    def __init__(self, directory=None):
        if directory is None:
            directory = os.environ.get("ASCENT_DATA_DIR")
        if directory is None:
            directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Ascent"
        self.path = Path(directory) / "profile.json"
        self.unit_names = {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            names = data.get("unit_names", {})
            if isinstance(names, dict):
                self.unit_names = {key: value for key, value in names.items() if isinstance(key, str) and isinstance(value, str) and value.strip() and len(value) <= 32}
        except (OSError, ValueError, AttributeError):
            pass

    def key(self, position):
        return f"{round(position[0])}:{round(position[1])}"

    def name_for(self, position, default):
        return self.unit_names.get(self.key(position), default)

    def save_name(self, position, name):
        names = {**self.unit_names, self.key(position): name}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"unit_names": names}, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            return False
        self.unit_names = names
        return True
