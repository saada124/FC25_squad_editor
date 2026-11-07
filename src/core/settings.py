"""
User Configuration and Application Settings for EA SPORTS FC 25 Squad Editor.
Persists user preferences across sessions in editor_settings.json.
"""
import os
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict

SETTINGS_FILENAME = "editor_settings.json"

@dataclass
class AppSettings:
    auto_backup_on_load: bool = True
    auto_backup_on_save: bool = True
    strict_clamping: bool = True
    max_backups_retain: int = 10
    confirm_discard_all: bool = True
    auto_apply_player_edits: bool = True
    show_tech_hashes_default: bool = False

    @classmethod
    def get_settings_path(cls) -> str:
        # Save in the application root directory
        return os.path.abspath(SETTINGS_FILENAME)

    @classmethod
    def load(cls) -> "AppSettings":
        path = cls.get_settings_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
            except Exception:
                pass
        return cls()

    def save(self):
        path = self.get_settings_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception:
            pass

