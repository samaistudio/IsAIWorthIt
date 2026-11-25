import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged

from ..wizard.usage_import import SMALL, UNMATCHED, summarise


def b64(text):
    return base64.b64encode(text.encode())


@tagged("post_install", "-at_install")
class TestImport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sales = cls.env["hr.department"].create({"name": "AIW Sales"})
        legal = cls.env["hr.department"].create({"name": "AIW Legal"})
        for i in range(6):
            cls.env["hr.employee"].create({"name": f"S{i}", "work_email": f"s{i}@example.com", "department_id": sales.id})
        for i in range(2):
            cls.env["hr.employee"].create({"name": f"L{i}", "work_email": f"l{i}@example.com", "department_id": legal.id})
        cls.env["isaiworthit.tool"].create({"name": "Test AI", "seats": 10, "cost_per_seat": 20, "minutes_per_action": 6})

    def test_summarise_combines_small_teams_and_calibrates(self):
        rows = [{"date": "2026-11-03", "user": f"s{i}@example.com", "tool": "T", "uses": "10"} for i in range(5)]
        rows += [{"date": "2026-11-03", "user": "l0@example.com", "tool": "T", "uses": "10"},
                 {"date": "2026-11-03", "user": "x@example.com", "tool": "T", "uses": "10"}]
        team_of = {f"s{i}@example.com": "Sales" for i in range(5)} | {"l0@example.com": "Legal"}
        survey = [{"month": "2026-11", "answer": "1-3 hours"}] * 5
        s = summarise(rows, survey, team_of, {"Legal"}, {"T": ("use", 6.0)})["2026-11"]
        self.assertEqual(s["users"], 7)
        self.assertAlmostEqual(s["bench_hours"], 7.0)            # 7 people x 10 uses x 6 min
        self.assertEqual(s["factor"], 4.0)                        # 2 h/week x 4.33 = 8.7 h vs 1 h -> capped at 4
        self.assertIn((SMALL, "T"), s["teams"])
        self.assertIn((UNMATCHED, "T"), s["teams"])
        self.assertNotIn(("Legal", "T"), s["teams"])
        self.assertNotIn("l0@example.com", repr(s))                # no person identifiers in the result

    def test_too_few_answers_keep_benchmark(self):
        rows = [{"date": "2026-11-03", "user": "a", "tool": "T", "uses": "1"}]
        s = summarise(rows, [{"month": "2026-11", "answer": "5+ hours"}] * 4, {}, set(), {"T": ("use", 60.0)})["2026-11"]
        self.assertEqual(s["factor"], 1.0)

    def test_wizard_creates_months_without_people(self):
        csv = "date,user,tool,uses,minutes\n" + "".join(
            f"2026-{m}-05,s{i}@example.com,Test AI,10,\n" for m in ("10", "11") for i in range(6)) + "2026-11-05,l0@example.com,Test AI,10,\n"
        wiz = self.env["isaiworthit.import"].create({"usage_file": b64(csv), "hourly_cost": 50})
        wiz.action_import()
        months = self.env["isaiworthit.month"].search([], order="month")
        self.assertEqual(months.mapped("label")[-2:], ["2026-10", "2026-11"])
        nov = months[-1]
        self.assertEqual(nov.active_users, 7)
        self.assertAlmostEqual(nov.hours_saved, 7.0)
        self.assertAlmostEqual(nov.value, 350.0)
        self.assertEqual(nov.licence_cost, 200.0)
        self.assertEqual(nov.net, 150.0)
        self.assertEqual(set(nov.result_ids.mapped("team")), {"AIW Sales", SMALL})
        tool = self.env["isaiworthit.tool"].search([("name", "=", "Test AI")])
        self.assertEqual(tool.unused_seats, 3)
        # re-importing the same month replaces it instead of failing
        self.env["isaiworthit.import"].create({"usage_file": b64(csv)}).action_import()
        self.assertEqual(self.env["isaiworthit.month"].search_count([("label", "=", "2026-11")]), 1)

    def test_semicolon_and_windows_1252_file(self):
        csv = "date;user;tool;uses;minutes\n" + "".join(f"2026-11-05;s{i}@example.com;Test AI;10;\n" for i in range(6))
        self.env["isaiworthit.import"].create({"usage_file": base64.b64encode(csv.encode("cp1252")), "hourly_cost": 50}).action_import()
        nov = self.env["isaiworthit.month"].search([("label", "=", "2026-11")])
        self.assertEqual(nov.active_users, 6)
        self.assertAlmostEqual(nov.hours_saved, 6.0)

    def test_bad_rows_give_a_clear_message(self):
        for row in ("2026-11-05,s0@example.com,Test AI,ten,", "03.11.2026,s0@example.com,Test AI,1,"):
            with self.subTest(row=row), self.assertRaises(UserError):
                self.env["isaiworthit.import"].create({"usage_file": b64("date,user,tool,uses,minutes\n" + row + "\n")}).action_import()


@tagged("post_install", "-at_install")
class TestAccess(TransactionCase):
    """Viewers see hours per team; money and the import are for managers only."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.viewer = new_test_user(cls.env, login="aiw_viewer", groups="base.group_user,isaiworthit.group_user")
        cls.month = cls.env["isaiworthit.month"].create({"month": "2026-11-01", "hours_saved": 10, "value": 450, "licence_cost": 100})

    def test_viewer_reads_hours_but_not_money(self):
        month = self.month.with_user(self.viewer)
        self.assertEqual(month.read(["hours_saved"])[0]["hours_saved"], 10)
        for field in ("value", "licence_cost", "net"):
            with self.subTest(field=field), self.assertRaises(AccessError):
                month.read([field])

    def test_viewer_cannot_import_or_change(self):
        with self.assertRaises(AccessError):
            self.env["isaiworthit.import"].with_user(self.viewer).create({"usage_file": b64("date,user,tool\n")})
        with self.assertRaises(AccessError):
            self.month.with_user(self.viewer).write({"hours_saved": 99})
