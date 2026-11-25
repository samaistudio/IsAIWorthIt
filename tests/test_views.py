"""Who sees what: data a reader may not see must be gone from their view, not just hidden."""
import json
import shutil
import unittest

from tests.helpers import demo_web, load

from core.measure import K_MIN
from core.views import for_everyone, for_management, markdown

MONEY_KEYS = {"spend_eur", "net_eur"}


class EveryoneView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = demo_web()
        cls.slugs = [b["slug"] for b in json.loads((cls.web / "data" / "businesses" / "index.json").read_text())]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.web, ignore_errors=True)

    def test_ten_demo_businesses(self):
        self.assertEqual(len(self.slugs), 10)

    def test_no_costs_teams_or_business_numbers(self):
        for slug in self.slugs:
            with self.subTest(slug=slug):
                ev = for_everyone(load(self.web, slug))
                self.assertFalse(MONEY_KEYS & set(ev["current"]))
                for m in ev["months"]:
                    self.assertFalse(MONEY_KEYS & set(m))
                self.assertEqual(ev["roles"], [])
                self.assertEqual(ev["kpis"], [])
                self.assertEqual(ev["tips"], [])
                for t in ev["tools"]:
                    self.assertEqual(set(t), {"tool", "active_users"})
                self.assertEqual(ev["measurement"]["evidence"], [])

    def test_evidence_is_removed_even_when_present(self):
        full = load(self.web, "it-services")
        full["measurement"] = {**full["measurement"],
                               "evidence": [{"name": "Invoices", "before": 1.0, "after": 2.0, "change": 1.0}]}
        ev = for_everyone(full)
        self.assertEqual(ev["measurement"]["evidence"], [])
        self.assertNotIn("Invoices", markdown(ev))
        self.assertIn("Invoices", markdown(for_management(full)))

    def test_everyone_markdown_has_no_costs(self):
        for slug in self.slugs:
            with self.subTest(slug=slug):
                text = markdown(for_everyone(load(self.web, slug)))
                for word in ("Licence costs", "Net benefit", "seats", "## Teams", "## Business numbers"):
                    self.assertNotIn(word, text)

    def test_same_totals_for_everyone_and_management(self):
        full = load(self.web, "tax-office")
        ev, mg = for_everyone(full), for_management(full)
        for k in ("active_users", "hours_saved", "value_eur"):
            self.assertEqual(ev["current"][k], mg["current"][k])


class SmallTeams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = demo_web()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.web, ignore_errors=True)

    def test_teams_under_k_min_carry_no_numbers(self):
        seen_hidden = False
        for f in (self.web / "data" / "businesses").glob("*.json"):
            if f.name == "index.json":
                continue
            for r in json.loads(f.read_text())["roles"]:
                with self.subTest(business=f.stem, team=r["role"]):
                    if r["hidden"]:
                        seen_hidden = True
                        self.assertNotIn("adoption", r)
                        self.assertNotIn("hours_saved", r)
                    else:
                        self.assertGreaterEqual(r["people"], K_MIN)
        self.assertTrue(seen_hidden, "the demo should include at least one hidden team")


if __name__ == "__main__":
    unittest.main()
