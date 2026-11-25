from tests.support import AppTestCase


class LoginRedirectTests(AppTestCase):
    def _login_with_next(self, next_value):
        return self.client.post(
            "/login",
            query_string={"next": next_value},
            data={"password": "test-password"},
        )

    def test_relative_next_is_honoured(self):
        resp = self._login_with_next("/stock")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["Location"], "/stock")

    def test_external_next_is_rejected(self):
        # 開放式重新導向：登入後不應被導到外部網站
        for evil in ("https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)"):
            with self.subTest(next=evil):
                resp = self._login_with_next(evil)
                self.assertEqual(resp.status_code, 302)
                self.assertEqual(resp.headers["Location"], "/")

    def test_wrong_password_does_not_log_in(self):
        resp = self.client.post("/login", data={"password": "nope"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("密碼錯誤", resp.get_data(as_text=True))
