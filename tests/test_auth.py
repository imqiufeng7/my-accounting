from unittest import mock

import config
from ledger import auth
from tests.support import AppTestCase


class CheckPasswordTests(AppTestCase):
    def test_non_ascii_input_does_not_crash(self):
        # secrets.compare_digest 對非 ASCII 字串會丟 TypeError，導致登入頁 500
        self.assertFalse(auth.check_password("中文密碼"))
        resp = self.client.post("/login", data={"password": "中文密碼"})
        self.assertEqual(resp.status_code, 200)

    def test_non_ascii_configured_password_works(self):
        with mock.patch.object(config, "APP_PASSWORD", "我的密碼123"):
            self.assertTrue(auth.check_password("我的密碼123"))
            self.assertFalse(auth.check_password("我的密碼124"))
