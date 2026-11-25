"""Builds the dashboard numbers for a real company from the local company database.
Time saved uses the three layers in measure.py: benchmarks, survey calibration, evidence."""
import sqlite3
from collections import defaultdict
from datetime import date

from .measure import K_MIN, benchmark_minutes, benchmarks, calibrate, evidence

TASK_LABEL = {"code": "Programming", "writing": "Writing texts", "research": "Research", "data": "Spreadsheets & data",
              "media": "Media", "admin": "Admin & planning", "other": "Other"}


def build(db_path, cfg, only_team=None):
    """only_team: a team name; that team and its sub-teams ('Sales / North') are kept, everything else is dropped."""
    company_factor = None
    if only_team:
        company_factor = (build(db_path, cfg)["measurement"]["calibration"] or {}).get("factor")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    comp = cfg.get("company", {})
    bench = benchmarks(cfg)
    default_rate = float(comp.get("default_hourly_cost", 45))

    people = {r["person"]: dict(r) for r in con.execute("SELECT * FROM people")}
    acts = [dict(r) for r in con.execute("SELECT * FROM activity WHERE person != ''")]
    seats = {r["tool"]: dict(r) for r in con.execute("SELECT * FROM seats")}
    for a in acts:
        people.setdefault(a["person"], {"person": a["person"], "team": None, "hourly_cost": None})
        a["task_key"] = a["task"].split(":")[0] if a["task"] else ""
        a["bench_min"] = benchmark_minutes(bench, a["tool"], a["task_key"], a["units"] or 1)

    if only_team:
        keep = {p for p, v in people.items() if v.get("team") and (v["team"] == only_team or v["team"].startswith(only_team + " / "))}
        people = {p: v for p, v in people.items() if p in keep}
        acts = [a for a in acts if a["person"] in keep]

    def rate(person):
        return float(people.get(person, {}).get("hourly_cost") or default_rate)

    months = sorted({a["day"][:7] for a in acts})[-6:] or [date.today().strftime("%Y-%m")]
    last = months[-1]

    # survey calibration, from the latest month that has enough answers
    survey = defaultdict(list)
    for r in con.execute("SELECT month, hours_week FROM survey"):
        survey[r["month"]].append(r["hours_week"])
    cal = {"factor": None, "n": 0, "month": None, "survey_hours_per_user": None, "benchmark_hours_per_user": None}
    for m in sorted(survey, reverse=True):
        ma = [a for a in acts if a["day"].startswith(m)]
        users = {a["person"] for a in ma}
        bh = sum(a["bench_min"] for a in ma) / 60 / len(users) if users else None
        factor, n, sh = calibrate(bh, survey[m])
        if factor:
            cal = {"factor": factor, "n": n, "month": m, "survey_hours_per_user": sh, "benchmark_hours_per_user": round(bh, 1),
                   "capped": factor in (0.25, 4.0)}
            break
    if only_team:  # a team uses the company-wide survey calibration
        cal = {"factor": company_factor, "n": None, "month": None, "survey_hours_per_user": None,
               "benchmark_hours_per_user": None, "capped": False}
    f = cal["factor"] or 1.0

    spend = 0 if only_team else sum(s["seats"] * s["price_eur"] for s in seats.values())
    per_month = []
    for m in months:
        ma = [a for a in acts if a["day"].startswith(m)]
        bench_h = sum(a["bench_min"] for a in ma) / 60
        value = sum(a["bench_min"] / 60 * rate(a["person"]) for a in ma) * f
        per_month.append({"month": m, "active_users": len({a["person"] for a in ma}), "hours_saved": round(bench_h * f, 1),
                          "benchmark_hours": round(bench_h, 1), "value_eur": round(value), "spend_eur": round(spend),
                          "net_eur": round(value - spend), "correction_rate": None})
    la = [a for a in acts if a["day"].startswith(last)]

    by = defaultdict(float)
    for a in la:
        by[TASK_LABEL.get(a["task_key"]) or a["tool"]] += a["bench_min"] / 60 * f
    tasks = [{"task": t, "hours_saved": round(h, 1)} for t, h in sorted(by.items(), key=lambda kv: -kv[1])]

    tools = []
    for t in sorted(set(seats) | {a["tool"] for a in la}):
        s = seats.get(t, {"seats": 0, "price_eur": 0})
        used = len({a["person"] for a in la if a["tool"] == t})
        unused = max(0, s["seats"] - used)
        tools.append({"tool": t, "seats": s["seats"], "active_users": used, "unused_seats": unused,
                      "monthly_cost_eur": round(s["seats"] * s["price_eur"]), "wasted_eur": round(unused * s["price_eur"])})

    teams = defaultdict(list)
    for p in people.values():
        if p.get("team"):
            teams[p["team"]].append(p["person"])
    roles = []
    for team, members in sorted(teams.items()):
        if len(members) < K_MIN:
            roles.append({"role": team, "people": len(members), "hidden": True})
            continue
        ms = set(members)
        roles.append({"role": team, "people": len(members), "hidden": False,
                      "adoption": round(len({a["person"] for a in la if a["person"] in ms}) / len(members), 2),
                      "hours_saved": round(sum(a["bench_min"] for a in la if a["person"] in ms) / 60 * f, 1)})

    kpis = defaultdict(dict)
    for r in con.execute("SELECT month, name, value FROM kpi ORDER BY month"):
        kpis[r["name"]][r["month"]] = r["value"]
    kpi_rows = [{"name": n, "first_month": min(s), "first": s[min(s)], "last_month": max(s), "last": s[max(s)]} for n, s in kpis.items()]
    ai_start = comp.get("ai_start_month") or (months[0] if acts else None)

    if only_team:
        tools = [{**t, "seats": None, "unused_seats": 0, "monthly_cost_eur": None, "wasted_eur": 0} for t in tools if t["active_users"]]
    return {"slug": "your-company", "name": (only_team + " · " if only_team else "") + comp.get("name", "Your company"), "industry": comp.get("industry", ""),
            "city": comp.get("city", ""), "people": len(people), "opted_in": len(people), "month": last,
            "current": per_month[-1], "months": per_month, "tasks": tasks, "tools": tools, "roles": roles,
            "tips": [], "kpis": [] if only_team else kpi_rows, "k_min": K_MIN, "real": True,
            "scope": {"level": "team", "team": only_team} if only_team else {"level": "company"},
            "measurement": {"method": "calibrated" if cal["factor"] else "benchmark", "calibration": cal,
                            "evidence": evidence(kpis, ai_start), "ai_start_month": ai_start}}
