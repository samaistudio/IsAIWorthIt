import base64
import csv
import io
from collections import defaultdict
from datetime import date
from statistics import median

from odoo import _, fields, models
from odoo.exceptions import UserError

K_MIN = 5            # teams smaller than this are combined, so no result points to one person
WEEKS_PER_MONTH = 4.33
SMALL = "Small teams (combined)"
UNMATCHED = "Not matched to an employee"
ANSWER_HOURS = {"none": 0, "0": 0, "less than 1 hour": .5, "under 1 h": .5, "<1h": .5, "1-3 hours": 2, "1–3 hours": 2,
                "1-3 h": 2, "3-5 hours": 4, "3–5 hours": 4, "more than 5 hours": 6, "5+ hours": 6, "3+ h": 4}


def _csv(data):
    """Rows of a CSV file. Accepts UTF-8 or Windows-1252 (German Excel) and ',' or ';' as separator."""
    raw = base64.b64decode(data)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    first = text.split("\n", 1)[0]
    delimiter = ";" if first.count(";") > first.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


class BadRow(ValueError):
    """A row the import cannot read; turned into a clear message for the user in action_import."""

    def __init__(self, row, column, value):
        super().__init__(row, column, value)
        self.row, self.column, self.value = row, column, value


def _number(value, row, column):
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        raise BadRow(row, column, value) from None


def _hours(answer):
    a = str(answer or "").strip().lower()
    try:
        return float(a.replace(",", "."))
    except ValueError:
        return ANSWER_HOURS.get(a)


def summarise(rows, survey, team_of, small_teams, bench):
    """Pure calculation, no database. Returns {month: {"users", "bench_hours", "factor", "answers",
    "teams": {(team, tool): {"users", "actions", "hours"}}}}. Person identifiers are only used
    inside this function to count distinct users and are never returned."""
    per = defaultdict(lambda: defaultdict(float))     # (month, user, tool) -> minutes
    acts = defaultdict(float)                          # (month, user, tool) -> counted uses
    days = set()                                       # (month, user, tool, day) for active-day tools
    for i, r in enumerate(rows, start=2):  # row 1 is the header
        day, user, tool = (r.get("date") or "").strip()[:10], (r.get("user") or "").strip().lower(), (r.get("tool") or "").strip()
        if not day or not user or not tool:  # empty lines and rows without a date are skipped, as before
            continue
        try:
            date.fromisoformat(day)
        except ValueError:
            raise BadRow(i, "date", r.get("date")) from None
        month, uses = day[:7], _number(r.get("uses") or 1, i, "uses")
        unit, minutes = bench.get(tool, ("use", 5.0))
        if (r.get("minutes") or "").strip():
            m = _number(r["minutes"], i, "minutes")
        elif unit == "active_day":
            if (month, user, tool, day) in days:
                m = 0
            else:
                days.add((month, user, tool, day))
                m = minutes
        else:
            m = minutes * max(uses, 1)
        per[(month, user)][tool] += m
        acts[(month, user, tool)] += uses

    answers = defaultdict(list)
    for s in survey:
        h = _hours(s.get("answer"))
        if h is not None and s.get("month"):
            answers[s["month"][:7]].append(h)

    out = {}
    for month in sorted({k[0] for k in per}):
        users = [u for (m, u) in per if m == month]
        bench_hours = sum(sum(per[(month, u)].values()) for u in users) / 60
        n = len(answers[month])
        factor = 1.0
        if n >= K_MIN and users and bench_hours:
            factor = round(max(.25, min(4.0, median(answers[month]) * WEEKS_PER_MONTH / (bench_hours / len(users)))), 2)
        teams = defaultdict(lambda: {"users": set(), "actions": 0.0, "hours": 0.0})
        for u in users:
            team = team_of.get(u, UNMATCHED)
            team = SMALL if team in small_teams else team
            for tool, minutes in per[(month, u)].items():
                t = teams[(team, tool)]
                t["users"].add(u)
                t["actions"] += acts[(month, u, tool)]
                t["hours"] += minutes / 60 * factor
        out[month] = {"users": len(users), "bench_hours": bench_hours, "factor": factor, "answers": n,
                      "teams": {k: {"users": len(v["users"]), "actions": v["actions"], "hours": v["hours"]} for k, v in teams.items()}}
    return out


class UsageImport(models.TransientModel):
    _name = "isaiworthit.import"
    _description = "Import AI usage"

    usage_file = fields.Binary("Usage CSV", required=True,
                               help="Columns: date, user (work e-mail), tool, uses, minutes (optional). "
                                    "Export from Microsoft 365, GitHub, ChatGPT or a shared sheet.")
    usage_filename = fields.Char()
    survey_file = fields.Binary("Survey CSV (optional)", help="Columns: month, answer. The anonymous monthly question "
                                                              "'About how much time did AI save you this week?'")
    survey_filename = fields.Char()
    hourly_cost = fields.Float("Average hourly cost", default=lambda self: float(
        self.env["ir.config_parameter"].sudo().get_param("isaiworthit.hourly_cost", 45)))

    def action_import(self):
        self.ensure_one()
        try:
            rows = _csv(self.usage_file)
            survey = _csv(self.survey_file) if self.survey_file else []
        except (UnicodeDecodeError, csv.Error, ValueError) as e:
            raise UserError(_("Could not read the file: %s", e))
        if not rows or not {"date", "user", "tool"} <= set(rows[0]):
            found = ", ".join(c for c in (rows[0] if rows else {}) if c) or _("none")
            raise UserError(_("The usage file needs the columns date, user and tool. Found: %s", found))

        company = self.env.company
        self.env["ir.config_parameter"].sudo().set_param("isaiworthit.hourly_cost", self.hourly_cost)
        Tool = self.env["isaiworthit.tool"].sudo()
        tools = {t.name: t for t in Tool.search([("company_id", "=", company.id)])}
        for name in {(r.get("tool") or "").strip() for r in rows} - set(tools) - {""}:
            tools[name] = Tool.create({"name": name, "company_id": company.id})
        bench = {n: (t.unit, t.minutes_per_action) for n, t in tools.items()}

        employees = self.env["hr.employee"].sudo().search([("company_id", "=", company.id)])
        team_of = {e.work_email.strip().lower(): e.department_id.name for e in employees if e.work_email and e.department_id}
        size = defaultdict(int)
        for e in employees.filtered("department_id"):
            size[e.department_id.name] += 1
        small = {d for d, n in size.items() if n < K_MIN}
        dept = {d.name: d for d in employees.mapped("department_id")}

        Month = self.env["isaiworthit.month"].sudo()
        licence = sum(t.monthly_cost for t in tools.values())
        made = Month
        try:
            months = summarise(rows, survey, team_of, small, bench)
        except BadRow as e:
            if e.column == "date":
                raise UserError(_("Row %(row)s: the date '%(value)s' must be written as YYYY-MM-DD.", row=e.row, value=e.value)) from None
            raise UserError(_("Row %(row)s: '%(value)s' in the column %(column)s is not a number.",
                              row=e.row, value=e.value, column=e.column)) from None
        for month, s in months.items():
            first = date(int(month[:4]), int(month[5:7]), 1)
            Month.search([("month", "=", first), ("company_id", "=", company.id)]).unlink()
            hours = sum(t["hours"] for t in s["teams"].values())
            made |= Month.create({
                "month": first, "company_id": company.id, "active_users": s["users"],
                "benchmark_hours": s["bench_hours"], "survey_answers": s["answers"], "calibration_factor": s["factor"],
                "hours_saved": hours, "hourly_cost": self.hourly_cost, "value": hours * self.hourly_cost,
                "licence_cost": licence,
                "result_ids": [(0, 0, {"team": team, "department_id": dept[team].id if team in dept else False,
                                       "tool_id": tools[tool].id, "active_users": t["users"], "actions": t["actions"],
                                       "hours_saved": t["hours"], "value": t["hours"] * self.hourly_cost})
                               for (team, tool), t in s["teams"].items()],
            })
        action = self.env["ir.actions.act_window"]._for_xml_id("isaiworthit.action_month")
        action["domain"] = [("id", "in", made.ids)]
        return action
