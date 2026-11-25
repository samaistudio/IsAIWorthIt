"""Command-line safety and the CSV connectors."""
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT

import isaiworthit
from core.connectors import REGISTRY, Store
from core.measure import calibrate


class SiteFolder(unittest.TestCase):
    """`isaiworthit.py site DIR` empties DIR first, so it must refuse folders that are not an earlier site."""

    def test_refuses_home_repo_and_parents(self):
        for p in (Path.home(), ROOT, ROOT.parent, Path(ROOT.anchor)):
            with self.subTest(path=p):
                self.assertIsNotNone(isaiworthit.site_dir_problem(p))

    def test_refuses_a_full_folder_without_marker(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "notes.txt").write_text("keep me")
            self.assertIsNotNone(isaiworthit.site_dir_problem(tmp))
            (tmp / ".nojekyll").write_text("")
            self.assertIsNone(isaiworthit.site_dir_problem(tmp))
        finally:
            shutil.rmtree(tmp)

    def test_accepts_a_new_folder(self):
        self.assertIsNone(isaiworthit.site_dir_problem(Path(tempfile.gettempdir()) / "iaw-new-site-folder"))


class CsvConnectors(unittest.TestCase):
    def test_usage_and_people_csv_store_no_e_mail_addresses(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            store = Store(tmp / "c.sqlite", "test-salt")
            n_usage = REGISTRY["usage_csv"]["run"](store, {"files": [str(ROOT / "examples" / "usage.csv")]})
            n_people = REGISTRY["people_csv"]["run"](store, {"file": str(ROOT / "examples" / "people.csv")})
            store.con.commit()
            store.con.close()
            self.assertGreater(n_usage, 0)
            self.assertGreater(n_people, 0)
            con = sqlite3.connect(tmp / "c.sqlite")
            dump = "\n".join(con.iterdump())
            con.close()
            self.assertNotIn("@example.com", dump)
        finally:
            shutil.rmtree(tmp)


class Calibration(unittest.TestCase):
    def test_needs_five_answers(self):
        self.assertEqual(calibrate(2.0, [1, 1, 1, 1])[0], None)

    def test_factor_is_limited(self):
        factor, n, _ = calibrate(0.1, [10] * 5)
        self.assertEqual((factor, n), (4.0, 5))


if __name__ == "__main__":
    unittest.main()
