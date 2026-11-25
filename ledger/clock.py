"""以使用者所在時區（預設台北）計算「今天」。

PythonAnywhere 等雲端主機的系統時區通常是 UTC，直接用 date.today()
會讓台灣時間 00:00～08:00 記的帳預設成前一天。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import config

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception

# 台灣沒有日光節約時間，找不到時區資料庫（例如 Windows 未安裝 tzdata）時以固定 UTC+8 代替
_FALLBACK_TZ = timezone(timedelta(hours=8), "UTC+08:00")


def _local_tz():
    if ZoneInfo is not None:
        try:
            return ZoneInfo(config.TIMEZONE)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return _FALLBACK_TZ


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def today_str() -> str:
    """回傳使用者時區的今天日期（YYYY-MM-DD）。"""
    return _utcnow().astimezone(_local_tz()).date().isoformat()
