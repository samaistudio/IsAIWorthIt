"""Who sees what. Data is removed before a report is written – a report file never contains
numbers its reader is not allowed to see.

  management   everything (the full dashboard)
  team lead    their team and its sub-teams, plus company averages for comparison;
               no licence costs, no other teams. Not produced for teams under 5 people.
  everyone     company totals and the kinds of work AI helps with; no team table, no costs.

Personal numbers are never in any report: each person sees their own only on their own
computer (Claude Code "My space").
"""
import json
import re
from pathlib import Path

from .company_metrics import build
from .measure import K_MIN


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def company_avg(full):
    c = full["current"]
    return {"adoption": round(c["active_users"] / max(1, full["opted_in"]), 2),
            "hours_per_user": round(c["hours_saved"] / max(1, c["active_users"]), 1)}


def for_management(full):
    return {**full, "scope": {"level": "management"}}


def for_team(db, cfg, team, full):
    d = build(db, cfg, only_team=team)
    if d["people"] < K_MIN:
        return None
    d["scope"] = {"level": "team", "team": team}
    d["roles"] = [r for r in d["roles"]]  # only this team and its sub-teams (build already filtered)
    d["compare"] = company_avg(full)
    d["measurement"] = {**d["measurement"], "evidence": []}  # company business numbers are management-only
    return d


def for_everyone(full):
    c = full["current"]
    keep = {k: full.get(k) for k in ("slug", "name", "industry", "city", "people", "opted_in", "month", "tasks", "k_min", "real")}
    # business numbers (evidence) are management-only, as in the team view and the dashboard
    keep["measurement"] = {**(full.get("measurement") or {}), "evidence": []}
    months = [{k: m[k] for k in ("month", "active_users", "hours_saved", "value_eur")} for m in full["months"]]
    return {**keep, "months": months, "current": {k: c[k] for k in ("month", "active_users", "hours_saved", "value_eur")},
            "tools": [{"tool": t["tool"], "active_users": t["active_users"]} for t in full["tools"] if t["active_users"]],
            "roles": [], "kpis": [], "tips": [], "scope": {"level": "everyone"}}


def markdown(d):
    """A plain summary to paste into ChatGPT, Claude or Copilot."""
    c, scope = d["current"], d.get("scope", {}).get("level", "company")
    who = {"management": "whole company", "company": "whole company", "team": f"team {d['scope'].get('team')} (incl. sub-teams)",
           "everyone": "company summary"}[scope]
    L = [f"# AI use report – {d['name']}", f"Scope: {who}. Month: {d['month']}. People: {d['people']}.",
         "All numbers are estimates; time saved = benchmarks per AI action"
         + (f", calibrated with a staff survey (×{d['measurement']['calibration']['factor']})" if (d.get("measurement") or {}).get("calibration", {}).get("factor") else "") + ".",
         "", "## This month", f"- People using AI: {c['active_users']}", f"- Hours saved: {c['hours_saved']}",
         f"- Value of time saved: €{c['value_eur']}"]
    if "spend_eur" in c and scope in ("management", "company"):
        L += [f"- Licence costs: €{c['spend_eur']}", f"- Net benefit: €{c['net_eur']}"]
    if d.get("compare"):
        L += [f"- Company average: {round(d['compare']['adoption'] * 100)}% of people use AI, {d['compare']['hours_per_user']} h saved per user"]
    L += ["", "## By month", "| Month | People using AI | Hours saved | Value € |" + (" Costs € | Net € |" if scope in ("management", "company") else ""),
          "|---|---|---|---|" + ("---|---|" if scope in ("management", "company") else "")]
    for m in d["months"]:
        L.append(f"| {m['month']} | {m['active_users']} | {m['hours_saved']} | {m['value_eur']} |"
                 + (f" {m['spend_eur']} | {m['net_eur']} |" if scope in ("management", "company") else ""))
    if d.get("tasks"):
        L += ["", "## Where time is saved", *[f"- {t['task']}: {t['hours_saved']} h" for t in d["tasks"]]]
    if d.get("roles"):
        L += ["", f"## Teams (only teams of {d['k_min']}+ people)"]
        L += [f"- {r['role']}: " + ("not shown (too small)" if r["hidden"] else f"{round(r['adoption'] * 100)}% use AI, {r['hours_saved']} h saved") for r in d["roles"]]
    if d.get("tools"):
        L += ["", "## Tools"]
        for t in d["tools"]:
            extra = f", {t['seats']} seats, €{t['monthly_cost_eur']}/month, {t['unused_seats']} unused" if t.get("seats") else ""
            L.append(f"- {t['tool']}: {t['active_users']} active{extra}")
    for e in (d.get("measurement") or {}).get("evidence") or []:
        L.append(f"- Evidence: {e['name']} per 100 booked hours {e['before']} → {e['after']} ({round(e['change'] * 100)}%)")
    if d.get("kpis"):
        L += ["", "## Business numbers", *[f"- {k['name']}: {k['first']} ({k['first_month']}) → {k['last']} ({k['last_month']})" for k in d["kpis"]]]
    L += ["", "No individual employees are shown. Groups under 5 people are left out."]
    return "\n".join(L) + "\n"


def html(d, template):
    data = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    # runs before the app bundle, so the app starts in report mode with only this reader's data
    return template.replace("<head>", f"<head><script>window.__DATA__ = {data};</script>", 1)


def write_reports(db, cfg, web_dir, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    template = (Path(web_dir) / "index.html").read_text(encoding="utf-8")
    access = cfg.get("access", {})
    full = build(db, cfg)
    made, skipped = [], []

    def save(name, d, readers):
        (out / f"{name}.html").write_text(html(d, template), encoding="utf-8")
        (out / f"{name}.md").write_text(markdown(d), encoding="utf-8")
        made.append((name, readers))

    if access.get("management"):
        save("management", for_management(full), access["management"])
    for team, leads in (access.get("team_leads") or {}).items():
        d = for_team(db, cfg, team, full)
        if d:
            save("team-" + slug(team), d, leads)
        else:
            skipped.append(f"{team} (fewer than {K_MIN} people)")
    if access.get("everyone", True):
        save("everyone", for_everyone(full), ["all staff"])
    index = ["# Reports", "", "Send each file only to the people listed. Each file contains only what its readers may see.", ""]
    index += [f"- `{n}.html` / `{n}.md` → {', '.join(r)}" for n, r in made]
    if skipped:
        index += ["", "Not created (privacy): " + ", ".join(skipped)]
    (out / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return made, skipped
