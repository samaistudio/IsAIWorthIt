"""Money-focused metrics for a small business. Business-wide numbers are always shown;
numbers per role are only shown for groups of 5 or more people who opted in."""
import json
from collections import defaultdict
from pathlib import Path

from .smb import PROFILES, TOOLS, generate

K_MIN = 5
TASK_LABEL = {"writing": "Writing texts", "email": "Emails", "research": "Research", "data": "Spreadsheets & data",
              "code": "Programming", "design": "Design", "translation": "Translation", "customer": "Customer replies",
              "admin": "Admin & planning"}


KPI = {"Tax advisory": ("Tax returns filed", 140), "Healthcare": ("Appointments handled", 1900), "Marketing": ("Deliverables shipped", 210),
       "Trades": ("Jobs invoiced", 260), "Real estate": ("Viewings arranged", 120), "E-commerce": ("Orders shipped", 2400),
       "IT services": ("Tickets closed", 610), "Architecture": ("Plan revisions delivered", 90), "Hospitality": ("Guest requests answered", 1500),
       "Legal": ("Briefs filed", 75)}


def build(profile):
    people, usage = generate(profile)
    opted = {p["id"] for p in people if p["opt_in"]}
    usage = [u for u in usage if u["person"] in opted]
    months = sorted({u["day"][:7] for u in usage} | {"2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"})
    seats = profile["tools"]
    spend_month = sum(TOOLS[t] * n for t, n in seats.items())

    per_month = []
    for m in months:
        mu = [u for u in usage if u["day"].startswith(m)]
        hours = sum(u["minutes_saved"] for u in mu) / 60
        value = sum(u["value_eur"] for u in mu)
        per_month.append({"month": m, "active_users": len({u["person"] for u in mu}), "hours_saved": round(hours, 1),
                          "value_eur": round(value), "spend_eur": spend_month, "net_eur": round(value - spend_month),
                          "correction_rate": round(sum(u["corrected"] for u in mu) / len(mu), 3) if mu else None})
    last = months[-1]
    last_name = __import__("datetime").date(int(last[:4]), int(last[5:]), 1).strftime("%B")
    lu = [u for u in usage if u["day"].startswith(last)]

    by_task = defaultdict(float)
    for u in lu:
        by_task[u["task"]] += u["minutes_saved"] / 60
    tasks = [{"task": TASK_LABEL[k], "hours_saved": round(v, 1)} for k, v in sorted(by_task.items(), key=lambda kv: -kv[1])]

    tools = []
    for t, n in seats.items():
        active = len({u["person"] for u in lu if u["tool"] == t})
        tools.append({"tool": t, "seats": n, "active_users": active, "unused_seats": max(0, n - active),
                      "monthly_cost_eur": TOOLS[t] * n, "wasted_eur": TOOLS[t] * max(0, n - active)})

    roles = []
    for role in dict.fromkeys(p["role"] for p in people):
        members = [p for p in people if p["role"] == role]
        ids = {p["id"] for p in members} & opted
        if len(ids) < K_MIN:
            roles.append({"role": role, "people": len(members), "hidden": True})
            continue
        ru = [u for u in lu if u["person"] in ids]
        roles.append({"role": role, "people": len(members), "hidden": False,
                      "adoption": round(len({u["person"] for u in ru}) / len(ids), 2),
                      "hours_saved": round(sum(u["minutes_saved"] for u in ru) / 60, 1)})

    tips = []
    waste = sum(t["wasted_eur"] for t in tools)
    if waste:
        worst = max(tools, key=lambda t: t["wasted_eur"])
        tips.append({"kind": "save", "text": f"{worst['unused_seats']} {worst['tool']} seat{'s were' if worst['unused_seats'] > 1 else ' was'} not used in {last_name}. "
                     f"Reassigning or cancelling them saves €{worst['wasted_eur']}/month."})
    visible = [r for r in roles if not r["hidden"]]
    if visible:
        low = min(visible, key=lambda r: r["adoption"])
        if low["adoption"] < .6:
            tips.append({"kind": "train", "text": f"Only {round(low['adoption'] * 100)}% of {low['role']} use AI. "
                         "A one-hour hands-on session usually lifts this quickly."})
    if tasks:
        tips.append({"kind": "grow", "text": f"Most time is saved on {tasks[0]['task'].lower()} ({tasks[0]['hours_saved']} h in {last_name}). "
                     "Share the prompts that work as a team template."})
    cr = per_month[-1]["correction_rate"]
    if cr and cr > .15:
        tips.append({"kind": "train", "text": f"AI answers needed fixing {round(cr * 100)}% of the time. "
                     "Giving the AI the goal, context and an example up front cuts this."})

    # Measurement layers, simulated for the demo: benchmarks are off by a business-specific bias,
    # the survey reflects what people actually save, and one business KPI improves after AI starts.
    import random as _r
    rr = _r.Random("measure-" + profile["slug"])
    bias = rr.uniform(.7, 1.45)
    cur_users = per_month[-1]["active_users"] or 1
    true_h = per_month[-1]["hours_saved"]
    n_survey = max(0, round(cur_users * rr.uniform(.55, .85)))
    factor = round(max(.25, min(4.0, 1 / bias)), 2)
    for m in per_month:
        m["benchmark_hours"] = round(m["hours_saved"] * bias, 1)
    start_m = per_month[min(len(per_month) - 1, profile["start"])]["month"]
    kpi_name, kpi_base = KPI.get(profile["industry"], ("Orders handled", 300))
    hours_month = len(people) * 150
    kpis, before, after = {}, [], []
    for i, m in enumerate(per_month):
        uplift = 1 + (rr.uniform(.06, .16) if m["month"] >= start_m and m["active_users"] else 0) * min(1, m["active_users"] / max(1, len(opted)) * 1.4)
        v = round(kpi_base * uplift * rr.uniform(.95, 1.05))
        kpis[m["month"]] = v
        (after if m["month"] >= start_m else before).append(v / hours_month * 100)
    ev = []
    if before and after:
        b, a = sum(before) / len(before), sum(after) / len(after)
        ev.append({"name": kpi_name, "before": round(b, 2), "after": round(a, 2), "change": round((a - b) / b, 3),
                   "months_before": len(before), "months_after": len(after)})
    measurement = {"method": "calibrated" if n_survey >= K_MIN else "benchmark",
                   "calibration": {"factor": factor if n_survey >= K_MIN else None, "n": n_survey, "month": last,
                                   "survey_hours_per_user": round(true_h / cur_users, 1),
                                   "benchmark_hours_per_user": round(true_h * bias / cur_users, 1), "capped": False},
                   "evidence": ev, "ai_start_month": start_m}
    if n_survey < K_MIN:  # without enough answers the dashboard falls back to the benchmark estimate
        for m in per_month:
            m["value_eur"] = round(m["value_eur"] * bias); m["hours_saved"] = m["benchmark_hours"]
            m["net_eur"] = m["value_eur"] - m["spend_eur"]
    kpi_rows = [{"name": kpi_name, "first_month": per_month[0]["month"], "first": kpis[per_month[0]["month"]],
                 "last_month": last, "last": kpis[last]}]

    cur = per_month[-1]
    return {"slug": profile["slug"], "name": profile["name"], "industry": profile["industry"], "city": profile["city"],
            "people": len(people), "opted_in": len(opted), "month": last, "current": cur, "months": per_month,
            "tasks": tasks, "tools": tools, "roles": roles, "tips": tips, "k_min": K_MIN,
            "kpis": kpi_rows, "measurement": measurement}


def export_all(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = []
    for p in PROFILES:
        data = build(p)
        (out / f"{p['slug']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
        index.append({"slug": p["slug"], "name": p["name"], "industry": p["industry"], "people": data["people"]})
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    return index
