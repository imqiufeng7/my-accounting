from __future__ import annotations
import json

import config


def load_settings() -> dict:
    if not config.SETTINGS_FILE.exists():
        save_settings(config.DEFAULT_SETTINGS)
        return dict(config.DEFAULT_SETTINGS)
    with open(config.SETTINGS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return {**config.DEFAULT_SETTINGS, **data}


def save_settings(settings: dict) -> None:
    config.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
