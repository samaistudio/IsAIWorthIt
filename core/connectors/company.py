"""Company data connectors: who belongs to which team, hourly costs, and business KPIs."""
import csv
from collections import defaultdict

from .base import connector, expand, http_json, secret


@connector("odoo", "Odoo", "company",
           "Teams and employees, booked hours, and monthly counts of sales orders, invoices, tickets, leads and tasks (whatever apps you use)",
           "Odoo external API (JSON-RPC) with a user's API key in the env variable you name.", "tested")
def odoo(store, cfg):
    from ..odoo import Odoo
    o = Odoo(cfg["url"], cfg["db"], cfg["user"], secret(cfg, "password_env"))
    n = 0
    # people and teams
    for e in o.x("hr.employee", "search_read", [], fields=["name", "work_email", "department_id"]):
        store.person(e.get("work_email") or e["name"], team=e["department_id"] and e["department_id"][1], source="odoo")
        n += 1
    # KPIs: count per month for every model this Odoo actually has
    have = {m["model"] for m in o.x("ir.model", "search_read", [], fields=["model"])}
    kpis = [
        ("account.analytic.line", "Booked hours", "date", [], "unit_amount"),
        ("sale.order", "Sales orders confirmed", "date_order", [["state", "=", "sale"]], None),
        ("account.move", "Customer invoices posted", "invoice_date", [["move_type", "=", "out_invoice"], ["state", "=", "posted"]], None),
        ("helpdesk.ticket", "Support tickets closed", "close_date", [["stage_id.fold", "=", True]], None),
        ("crm.lead", "Deals won", "date_closed", [["stage_id.is_won", "=", True]], None),
        ("project.task", "Tasks completed", "date_end", [["state", "=", "1_done"]], None),
    ]
    for model, name, field, domain, measure in kpis:
        if model not in have:
            continue
        fields = [f"{measure}:sum"] if measure else ["__count"]
        rows = o.x(model, "read_group", domain + [[field, "!=", False]], fields, [f"{field}:month"], lazy=False, context={"lang": "en_US"})
        for r in rows:
            rng = (r.get("__range") or {}).get(f"{field}:month") or {}
            month = (rng.get("from") or "")[:7] or _month(r.get(f"{field}:month") or r.get(field))
            if month:
                store.kpi(month, name, round(r.get(measure) or r.get("__count") or 0, 1), "odoo")
                n += 1
    return n


def _month(label):
    import re
    from datetime import datetime
    if not label:
        return None
    m = re.match(r"(\d{4})-(\d{2})", str(label))
    if m:
        return f"{m[1]}-{m[2]}"
    for fmt in ("%B %Y", "%b %Y"):
        try:
            return datetime.strptime(str(label), fmt).strftime("%Y-%m")
        except ValueError:
            pass
    return None


@connector("personio", "Personio", "company",
           "Employees and departments (teams)",
           "Personio API v1 with client ID and secret in the env variables you name.", "docs")
def personio(store, cfg):
    token = http_json("https://api.personio.de/v1/auth", data={"client_id": secret(cfg, "client_id_env"),
                                                             "client_secret": secret(cfg, "client_secret_env")},
                      method="POST")["data"]["token"]
    res = http_json("https://api.personio.de/v1/company/employees", {"Authorization": f"Bearer {token}"})
    n = 0
    for e in res.get("data", []):
        a = e.get("attributes", {})
        val = lambda k: (a.get(k) or {}).get("value")
        dept = val("department")
        store.person(val("email") or f"{val('first_name')} {val('last_name')}",
                     team=dept.get("attributes", {}).get("name") if isinstance(dept, dict) else dept, source="personio")
        n += 1
    return n


@connector("people_csv", "Team list (CSV)", "company",
           "Who is in which team, and the hourly cost per person or team",
           "A CSV with the columns: user, team, hourly_cost (hourly_cost optional). Use the same user IDs or e-mails as your AI tool exports.", "tested")
def people_csv(store, cfg):
    n = 0
    with open(expand(cfg["file"]), newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            store.person(row["user"], team=row.get("team") or None,
                         hourly_cost=float(row["hourly_cost"]) if row.get("hourly_cost") else None, source="people_csv")
            n += 1
    return n


@connector("kpi_csv", "Your own KPIs (CSV)", "company",
           "Any monthly number you track: orders, calls, tickets, revenue",
           "A CSV with the columns: month (YYYY-MM), name, value.", "tested")
def kpi_csv(store, cfg):
    n = 0
    with open(expand(cfg["file"]), newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            store.kpi(row["month"][:7], row["name"], float(row["value"]), "kpi_csv")
            n += 1
    return n


@connector("licences", "Licences and prices", "company",
           "Seats bought per AI tool and the monthly price per seat",
           "Listed in the config file under connectors.licences.tools.", "tested")
def licences(store, cfg):
    for tool, v in cfg.get("tools", {}).items():
        store.seats(tool, int(v["seats"]), float(v["price_eur"]))
    return len(cfg.get("tools", {}))


@connector("survey_csv", "Time-saved survey (CSV)", "company",
           "Anonymous monthly answers to: About how much time did AI save you this week?",
           "Run the one-question form in Microsoft Forms or Google Forms (see docs/SURVEY.md), export the answers as CSV. "
           "Columns: month (YYYY-MM), answer, team (optional). Used only when at least 5 people answered.", "tested")
def survey_csv(store, cfg):
    from ..measure import answer_to_hours
    store.con.execute("DELETE FROM survey WHERE source = 'survey_csv'")
    n = 0
    for f in cfg.get("files", []):
        with open(expand(f), newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                h = answer_to_hours(row.get("answer", ""))
                if h is not None:
                    store.survey(row["month"][:7], row.get("team") or None, h, "survey_csv")
                    n += 1
    return n
