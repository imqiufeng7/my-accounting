import config
from ledger import storage
from tests.support import AppTestCase


class FormNormalisationTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_stock_edit_defaults_empty_rate_to_one(self):
        self.post("/stock", data={"日期": "2026-01-01", "股票代號": "2330", "交易類型": "買", "股數": "1", "單價": "10"})
        row = storage.read_rows(config.STOCK_FILE, config.STOCK_FIELDS)[0]
        self.assertEqual(row["匯率"], "1")
        self.post(f"/stock/{row['id']}/edit", data={"日期": "2026-01-01", "股票代號": " 2330 ", "交易類型": "買",
                                                   "股數": "1", "單價": "10", "匯率": ""})
        row = storage.read_rows(config.STOCK_FILE, config.STOCK_FIELDS)[0]
        self.assertEqual(row["匯率"], "1")
        self.assertEqual(row["股票代號"], "2330")

    def test_batch_rows_share_header_and_default_rate(self):
        self.post("/travel/batch", data={
            "目的地": "東京", "日期": "2026-01-01", "類別": "餐", "付款人": "A", "分攤對象": "A,B",
            "項目[]": ["拉麵", "", "壽司"], "金額[]": ["300", "100", "500"],
        })
        cfg = config.MODE_CONFIG["travel"]
        rows = storage.read_rows(cfg["file"], cfg["fields"])
        self.assertEqual([(r["項目"], r["金額"], r["匯率"], r["目的地"]) for r in rows],
                         [("拉麵", "300", "1", "東京"), ("壽司", "500", "1", "東京")])

    def test_expense_edit_keeps_id(self):
        self.post("/personal", data={"日期": "2026-01-01", "項目": "a", "金額": "1"})
        cfg = config.MODE_CONFIG["personal"]
        row = storage.read_rows(cfg["file"], cfg["fields"])[0]
        self.post(f"/personal/{row['id']}/edit", data={"日期": "2026-01-02", "項目": "b", "金額": "2", "id": "hacked"})
        updated = storage.read_rows(cfg["file"], cfg["fields"])[0]
        self.assertEqual((updated["id"], updated["項目"], updated["匯率"]), (row["id"], "b", "1"))
