from __future__ import annotations
import secrets
from datetime import date

import config
from ledger import storage

PUBLIC_ENDPOINTS = {"login", "share_travel", "static"}


def check_password(password: str) -> bool:
    return secrets.compare_digest(password, config.APP_PASSWORD)


def get_or_create_share_token(destination: str) -> str:
    rows = storage.read_rows(config.TRAVEL_SHARES_FILE, config.TRAVEL_SHARES_FIELDS)
    for row in rows:
        if row.get("目的地") == destination:
            return row["token"]

    token = secrets.token_urlsafe(16)
    storage.upsert_keyed_row(
        config.TRAVEL_SHARES_FILE,
        config.TRAVEL_SHARES_FIELDS,
        "token",
        token,
        {"目的地": destination, "建立日期": date.today().isoformat()},
    )
    return token


def resolve_share_token(token: str) -> str | None:
    rows = storage.read_rows(config.TRAVEL_SHARES_FILE, config.TRAVEL_SHARES_FIELDS)
    for row in rows:
        if row.get("token") == token:
            return row["目的地"]
    return None
