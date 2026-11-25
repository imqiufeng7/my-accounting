from datetime import datetime, timezone
from unittest import mock

import config
from ledger import auth, clock, storage
from tests.support import AppTestCase

# UTC 2026-01-01 20:30 = 台北 2026-01-02 04:30：伺服器若用 UTC 會算成前一天
LATE_NIGHT_UTC = datetime(2026, 1, 1, 20, 30, tzinfo=timezone.utc)


class ClockTests(AppTestCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(clock, "_utcnow", return_value=LATE_NIGHT_UTC)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_today_uses_taipei_time(self):
        self.assertEqual(clock.today_str(), "2026-01-02")

    def test_fallback_offset_when_zone_missing(self):
        with mock.patch.object(config, "TIMEZONE", "No/Such_Zone"):
            self.assertEqual(clock.today_str(), "2026-01-02")

    def test_entry_form_defaults_to_local_today(self):
        self.login()
        for page in ("/personal", "/personal/batch", "/stock", "/accounts"):
            with self.subTest(page=page):
                html = self.client.get(page).get_data(as_text=True)
                self.assertIn('name="日期" value="2026-01-02"' if page != "/accounts" else 'name="期初日期" value="2026-01-02"', html)

    def test_price_update_and_share_token_dates(self):
        self.login()
        self.post("/stock/prices", data={"股票代號": "2330", "目前市價": "1000"})
        rows = storage.read_rows(config.STOCK_PRICES_FILE, config.STOCK_PRICES_FIELDS)
        self.assertEqual(rows[0]["更新日期"], "2026-01-02")

        auth.get_or_create_share_token("東京")
        shares = storage.read_rows(config.TRAVEL_SHARES_FILE, config.TRAVEL_SHARES_FIELDS)
        self.assertEqual(shares[0]["建立日期"], "2026-01-02")
