"""測試共用工具：把所有資料檔導向暫存目錄，避免動到真實 data/。"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# 在匯入 app 之前先給定測試用密碼與金鑰
os.environ.setdefault("APP_PASSWORD", "test-password")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

import config  # noqa: E402


class TempDataTestCase(unittest.TestCase):
    """每個測試都使用全新的暫存資料目錄。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        patches = {
            "DATA_DIR": self.data_dir,
            "STOCK_FILE": self.data_dir / "stock.csv",
            "STOCK_PRICES_FILE": self.data_dir / "stock_prices.csv",
            "ACCOUNTS_FILE": self.data_dir / "accounts.csv",
            "TRAVEL_SHARES_FILE": self.data_dir / "travel_shares.csv",
            "SETTINGS_FILE": self.data_dir / "settings.json",
            "APP_PASSWORD": "test-password",
        }
        self._patchers = [mock.patch.object(config, k, v) for k, v in patches.items()]
        mode_config = {
            mode: {**cfg, "file": self.data_dir / Path(cfg["file"]).name}
            for mode, cfg in config.MODE_CONFIG.items()
        }
        self._patchers.append(mock.patch.dict(config.MODE_CONFIG, mode_config))
        for p in self._patchers:
            p.start()

    def tearDown(self):
        for p in reversed(self._patchers):
            p.stop()
        self._tmp.cleanup()


class AppTestCase(TempDataTestCase):
    """提供已設定好的 Flask 測試用戶端。"""

    def setUp(self):
        super().setUp()
        from app import app

        app.config["TESTING"] = True
        self.app = app
        self.client = app.test_client()

    def login(self):
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
