import config
from ledger import aggregator, storage
from tests.support import AppTestCase


class AccountRoutesTests(AppTestCase):
    def test_account_with_slash_in_name_can_be_deleted(self):
        # 「台新/信用卡」這類名稱原本會產生 %2F 網址，路由比對不到而 404，無法刪除
        self.login()
        self.post("/accounts", data={"帳戶名稱": "台新/信用卡", "期初餘額": "0", "期初日期": "2026-01-01"})
        html = self.client.get("/accounts").get_data(as_text=True)
        self.assertIn("台新/信用卡", html)
        from flask import url_for
        with self.app.test_request_context():
            url = url_for("account_delete", name="台新/信用卡")
        resp = self.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(storage.read_rows(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS), [])

    def test_balance_reflects_expenses_and_stock_trades(self):
        self.login()
        self.post("/accounts", data={"帳戶名稱": "銀行", "期初餘額": "10000", "匯率": "1", "期初日期": "2026-01-01"})
        self.post("/personal", data={"日期": "2026-01-02", "類別": "餐", "項目": "飯", "金額": "100", "付款方式": "銀行"})
        self.post("/personal", data={"日期": "2025-12-31", "類別": "餐", "項目": "舊", "金額": "999", "付款方式": "銀行"})
        self.post("/stock", data={"日期": "2026-01-03", "股票代號": "2330", "交易類型": "買", "股數": "2",
                                  "單價": "1000", "手續費": "20", "付款方式": "銀行"})
        total, details = aggregator.account_balances()
        # 10000 - 100（期初日前的 999 不算）- (2000 + 20)
        self.assertEqual(total, 7880)
        self.assertEqual(details[0]["balance_twd"], 7880)
