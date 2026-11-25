import re

import config
from ledger import storage
from tests.support import AppTestCase


class CsrfTests(AppTestCase):
    def setUp(self):
        super().setUp()
        cfg = config.MODE_CONFIG["personal"]
        self.row = storage.append_row(cfg["file"], cfg["fields"], {"日期": "2026-11-01", "項目": "午餐", "金額": "100"})
        self.cfg = cfg

    def _row_count(self):
        return len(storage.read_rows(self.cfg["file"], self.cfg["fields"]))

    def test_delete_without_token_is_rejected(self):
        self.login()
        resp = self.client.post(f"/personal/{self.row['id']}/delete")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self._row_count(), 1)

    def test_delete_with_wrong_token_is_rejected(self):
        self.login()
        resp = self.client.post(f"/personal/{self.row['id']}/delete", data={"csrf_token": "forged"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self._row_count(), 1)

    def test_delete_with_token_succeeds(self):
        self.login()
        resp = self.post(f"/personal/{self.row['id']}/delete")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self._row_count(), 0)

    def test_every_post_form_renders_token(self):
        # 所有含 POST 表單的頁面都要帶出 token，否則正常使用者也會被擋
        self.login()
        pages = ["/", "/personal", "/personal/batch", f"/personal/{self.row['id']}/edit",
                 "/travel/settlement", "/stock", "/stock/prices", "/accounts", "/settings"]
        storage.upsert_keyed_row(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS, "帳戶名稱", "現金", {})
        for page in pages:
            with self.subTest(page=page):
                html = self.client.get(page).get_data(as_text=True)
                forms = re.findall(r"<form[^>]*method=\"post\"[^>]*>(.*?)</form>", html, flags=re.S)
                self.assertTrue(forms, f"{page} 沒有 POST 表單？")
                for form in forms:
                    self.assertIn(f'name="csrf_token" value="{self.CSRF}"', form)

    def test_login_page_issues_token(self):
        html = self.client.get("/login").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
        resp = self.client.post("/login", data={"password": "test-password", "csrf_token": token})
        self.assertEqual(resp.status_code, 302)
