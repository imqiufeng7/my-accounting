import threading
import unittest
from multiprocessing import get_context

import config
from ledger import storage
from tests.support import TempDataTestCase

FIELDS = config.EXPENSE_FIELDS


def _append_many(path, count):
    for i in range(count):
        storage.append_row(path, FIELDS, {"項目": f"p{i}", "金額": "1"})


class StorageConcurrencyTests(TempDataTestCase):
    def test_concurrent_thread_appends_are_not_lost(self):
        path = self.data_dir / "personal.csv"
        threads = [threading.Thread(target=_append_many, args=(path, 25)) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(storage.read_rows(path, FIELDS)), 8 * 25)

    def test_concurrent_process_appends_are_not_lost(self):
        # PythonAnywhere 等 WSGI 主機可能同時跑多個 worker 行程
        path = self.data_dir / "work.csv"
        storage.ensure_csv(path, FIELDS)
        ctx = get_context("fork")
        procs = [ctx.Process(target=_append_many, args=(path, 25)) for _ in range(4)]
        for p in procs:
            p.start()
        for p in procs:
            p.join()
        self.assertEqual(len(storage.read_rows(path, FIELDS)), 4 * 25)

    def test_update_and_delete_still_work(self):
        path = self.data_dir / "personal.csv"
        row = storage.append_row(path, FIELDS, {"項目": "a", "金額": "1"})
        self.assertTrue(storage.update_row(path, FIELDS, row["id"], {"金額": "2"}))
        self.assertEqual(storage.read_rows(path, FIELDS)[0]["金額"], "2")
        self.assertTrue(storage.delete_row(path, FIELDS, row["id"]))
        self.assertFalse(storage.delete_row(path, FIELDS, row["id"]))


if __name__ == "__main__":
    unittest.main()
