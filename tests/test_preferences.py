import config
from ledger import preferences
from tests.support import AppTestCase


class PreferencesTests(AppTestCase):
    def test_corrupt_settings_file_falls_back_to_defaults(self):
        # 寫到一半中斷的 settings.json 原本會讓所有記帳頁面 500
        for bad in ('{"預設付款人": "A"', "[1, 2]", ""):
            with self.subTest(content=bad):
                config.SETTINGS_FILE.write_text(bad, encoding="utf-8")
                self.assertEqual(preferences.load_settings(), config.DEFAULT_SETTINGS)
                self.login()
                self.assertEqual(self.client.get("/personal").status_code, 200)

    def test_save_and_load_round_trip(self):
        preferences.save_settings({"預設付款人": "小明", "預設付款方式": "現金"})
        self.assertEqual(preferences.load_settings()["預設付款人"], "小明")
        # 原子寫入不應留下暫存檔
        self.assertEqual([p.name for p in config.SETTINGS_FILE.parent.iterdir()], ["settings.json"])
