from __future__ import annotations
import json
import os
import uuid

import config


def load_settings() -> dict:
    if not config.SETTINGS_FILE.exists():
        save_settings(config.DEFAULT_SETTINGS)
        return dict(config.DEFAULT_SETTINGS)
    try:
        with open(config.SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        # 檔案損毀（例如寫到一半中斷）時退回預設值，不要讓所有記帳頁面 500
        return dict(config.DEFAULT_SETTINGS)
    if not isinstance(data, dict):
        return dict(config.DEFAULT_SETTINGS)
    return {**config.DEFAULT_SETTINGS, **data}


def save_settings(settings: dict) -> None:
    config.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    # 先寫暫存檔再 os.replace，避免中途中斷留下半個 JSON
    tmp_path = config.SETTINGS_FILE.parent / f".{config.SETTINGS_FILE.name}.{uuid.uuid4().hex}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, config.SETTINGS_FILE)
