"""AI tool usage connectors."""
import csv
import getpass
from datetime import date, timedelta

from .base import connector, expand, http_json, secret


@connector("claude_code_local", "Claude Code (this computer)", "ai",
           "Sessions, active minutes, tools, corrections per day",
           "Reads ~/.claude/projects on this computer. Each person runs it on their own machine (opt-in).", "tested")
def claude_code_local(store, cfg):
    from ..parsers.claude_code import iter_sessions
    who = store.person(cfg.get("person") or getpass.getuser(), team=cfg.get("team"), source="claude_code_local")
    n = 0
    for s in iter_sessions(expand(cfg.get("path", "~/.claude/projects"))):
        store.activity(s["started_at"][:10], who, "Claude Code", "claude_code_local", units=1,
                       minutes=s["active_minutes"], task=s["task_type"] + ":" + s["id"][:8],
                       corrections=s["correction_turns"])
        n += 1
    return n


@connector("anthropic_admin", "Claude Code (whole team, Anthropic Admin API)", "ai",
           "Per person and day: sessions, lines of code, commits, pull requests",
           "Claude Code Analytics API with an Admin API key (sk-ant-admin…) in the env variable you name.", "docs")
def anthropic_admin(store, cfg):
    key = secret(cfg, "api_key_env")
    days = int(cfg.get("days", 30))
    n = 0
    for i in range(days, 0, -1):
        day = (date.today() - timedelta(days=i)).isoformat()
        page = None
        while True:
            url = f"https://api.anthropic.com/v1/organizations/usage_report/claude_code?starting_at={day}&limit=1000"
            if page:
                url += f"&page={page}"
            res = http_json(url, {"x-api-key": key, "anthropic-version": cfg.get("api_version", "2023-06-01")})
            for rec in res.get("data", []):
                actor = rec.get("actor") or {}
                who = store.person(actor.get("email_address") or actor.get("api_key_name") or "unknown", source="anthropic_admin")
                core = rec.get("core_metrics") or {}
                store.activity(day, who, "Claude Code", "anthropic_admin", units=core.get("num_sessions", 1))
                n += 1
            page = res.get("next_page")
            if not res.get("has_more") or not page:
                break
    return n


@connector("m365_copilot_csv", "Microsoft 365 Copilot", "ai",
           "Per person: last day they used Copilot, per app (anonymised by default)",
           "Export the per-user table in the Microsoft 365 admin center (Reports → Usage → Copilot) and list the CSV files. "
           "Export once a month to build up history.", "docs")
def m365_copilot_csv(store, cfg):
    n = 0
    for f in cfg.get("files", []):
        with open(expand(f), newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                key = {k.lower().strip(): v for k, v in row.items() if k}
                user = key.get("user principal name") or key.get("display name") or ""
                last = key.get("last activity date") or key.get("last activity date (utc)") or ""
                if not user or not last:
                    continue
                who = store.person(user, source="m365_copilot_csv")
                store.activity(last[:10], who, "Microsoft 365 Copilot", "m365_copilot_csv", units=1)
                n += 1
    return n


@connector("github_copilot", "GitHub Copilot", "ai",
           "Daily active and engaged users for the organisation (no per-person data)",
           "GitHub Copilot metrics API with an org admin token in the env variable you name. "
           "GitHub announced a newer usage-metrics API; this connector may need updating.", "docs")
def github_copilot(store, cfg):
    token = secret(cfg, "token_env")
    res = http_json(f"https://api.github.com/orgs/{cfg['org']}/copilot/metrics",
                    {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"})
    n = 0
    for day in res:
        # Org-level only: store as anonymous "seat slots" so adoption can still be counted.
        for i in range(int(day.get("total_active_users", 0))):
            store.activity(day["date"], f"gh-active-{i}", "GitHub Copilot", "github_copilot", units=1)
        n += 1
    return n


@connector("usage_csv", "Any AI tool (CSV)", "ai",
           "Per person and day: tool, number of uses, optional minutes",
           "A CSV with the columns: date, user, tool, uses, minutes (minutes optional). Works for ChatGPT, Gemini, DeepL, Canva, Perplexity …", "tested")
def usage_csv(store, cfg):
    n = 0
    for f in cfg.get("files", []):
        with open(expand(f), newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                who = store.person(row["user"], source="usage_csv")
                minutes = float(row["minutes"]) if row.get("minutes") else None
                store.activity(row["date"][:10], who, row["tool"], "usage_csv", units=float(row.get("uses") or 1), minutes=minutes)
                n += 1
    return n
