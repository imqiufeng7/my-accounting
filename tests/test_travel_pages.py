import config
from ledger import auth, storage
from tests.support import AppTestCase


class TravelPagesRobustnessTests(AppTestCase):
    def setUp(self):
        super().setUp()
        cfg = config.MODE_CONFIG["travel"]
        storage.append_row(cfg["file"], cfg["fields"], {
            "目的地": "東京", "日期": "2026-11-01", "類別": "餐飲", "項目": "拉麵",
            "金額": "300", "匯率": "1", "付款人": "A", "分攤對象": "A:abc,B",
        })

    def test_public_share_page_survives_malformed_weight(self):
        token = auth.get_or_create_share_token("東京")
        resp = self.client.get(f"/share/travel/{token}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("150.00", resp.get_data(as_text=True))

    def test_settlement_page_survives_malformed_weight(self):
        self.login()
        resp = self.client.get("/travel/settlement", query_string={"目的地": "東京"})
        self.assertEqual(resp.status_code, 200)
