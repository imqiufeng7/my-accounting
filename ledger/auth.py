from __future__ import annotations
import secrets
from datetime import date

import config
from ledger import storage

PUBLIC_ENDPOINTS = {"login", "share_travel", "static"}

CSRF_SESSION_KEY = "_csrf_token"
CSRF_FORM_FIELD = "csrf_token"


def csrf_token() -> str:
    """取得（必要時建立）存在 session 中的 CSRF token，供樣板放進隱藏欄位。"""
    from flask import session

    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def csrf_is_valid(submitted: str | None) -> bool:
    from flask import session

    expected = session.get(CSRF_SESSION_KEY)
    if not expected or not submitted:
        return False
    return secrets.compare_digest(submitted.encode("utf-8"), expected.encode("utf-8"))


def check_password(password: str) -> bool:
    # compare_digest 遇到非 ASCII 的 str 會丟 TypeError，先轉成 UTF-8 位元組再比對
    return secrets.compare_digest(password.encode("utf-8"), config.APP_PASSWORD.encode("utf-8"))


def safe_next_url(target: str | None) -> str | None:
    """只允許站內相對路徑，避免登入後被導向外部網站（開放式重新導向）。"""
    if not target:
        return None
    # 瀏覽器會把反斜線當成斜線，"/\\evil.com" 等同 "//evil.com"
    normalized = target.replace("\\", "/")
    if not normalized.startswith("/") or normalized.startswith("//"):
        return None
    if any(ord(ch) < 32 for ch in normalized):
        return None
    return target


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
