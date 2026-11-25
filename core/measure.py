"""How IsAIWorthIt measures time saved. Three layers, each shown separately in the dashboard:

1. Benchmarks   standard minutes saved per AI action (per tool, and per type of work where known).
                Automatic from day one, but an average. All values are starting points and can be
                changed in the config under company.benchmarks.
2. Survey       one anonymous question a month: "About how much time did AI save you this week?"
                If at least 5 people answered, the benchmark estimate is scaled to match what people
                report (calibration factor, limited to 0.25x-4x so one odd month cannot run away).
3. Evidence     business output per booked hour (from Odoo or your own KPIs), before vs. after the
                month AI was introduced. Shown as supporting evidence, not mixed into the hours.
"""
from statistics import median

K_MIN = 5
WEEKS_PER_MONTH = 4.33

# unit: what one counted activity means for this tool
DEFAULT_BENCHMARKS = {
    "Microsoft 365 Copilot": {"unit": "active_day", "minutes": 15},
    "GitHub Copilot": {"unit": "active_day", "minutes": 30},
    "ChatGPT Team": {"unit": "use", "minutes": 6},
    "Gemini for Workspace": {"unit": "use", "minutes": 6},
    "DeepL Pro": {"unit": "use", "minutes": 3},
    "Canva AI": {"unit": "use", "minutes": 10},
    "Claude Code": {"unit": "session", "minutes": 12,
                    "by_task": {"code": 30, "writing": 15, "research": 15, "data": 20, "media": 15, "admin": 8}},
    "default": {"unit": "use", "minutes": 5},
}

# answers from Microsoft Forms / Google Forms; numbers are taken as hours per week
ANSWER_HOURS = {"none": 0, "0": 0, "less than 1 hour": .5, "under 1 h": .5, "<1h": .5, "1-3 hours": 2, "1–3 hours": 2,
                "1-3 h": 2, "3-5 hours": 4, "3–5 hours": 4, "more than 5 hours": 6, "5+ hours": 6, "3+ h": 4}


def benchmarks(cfg):
    merged = {k: dict(v) for k, v in DEFAULT_BENCHMARKS.items()}
    for tool, v in (cfg.get("company", {}).get("benchmarks") or {}).items():
        merged.setdefault(tool, {}).update(v)
    return merged


def benchmark_minutes(bench, tool, task, units):
    b = bench.get(tool) or bench["default"]
    per = (b.get("by_task") or {}).get(task, b["minutes"])
    # "use" and "session" scale with the count; an "active day" counts once per day
    return per * (1 if b["unit"] == "active_day" else max(units, 1))


def answer_to_hours(answer):
    a = str(answer).strip().lower()
    try:
        return float(a.replace(",", "."))
    except ValueError:
        return ANSWER_HOURS.get(a)


def calibrate(benchmark_hours_per_user, survey_hours_week):
    """Returns (factor, n, survey_hours_per_user_month). factor is None if there are too few answers."""
    answers = [h for h in survey_hours_week if h is not None]
    if len(answers) < K_MIN or not benchmark_hours_per_user:
        return None, len(answers), None
    survey_month = median(answers) * WEEKS_PER_MONTH
    factor = max(.25, min(4.0, survey_month / benchmark_hours_per_user))
    return round(factor, 2), len(answers), round(survey_month, 1)


def evidence(kpis, ai_start):
    """Output per 100 booked hours, before vs. after AI. kpis: {name: {month: value}}."""
    hours = kpis.get("Booked hours")
    if not hours or not ai_start:
        return []
    out = []
    for name, series in kpis.items():
        if name == "Booked hours":
            continue
        before = [series[m] / hours[m] * 100 for m in series if m in hours and m < ai_start and hours[m]]
        after = [series[m] / hours[m] * 100 for m in series if m in hours and m >= ai_start and hours[m]]
        if before and after:
            b, a = sum(before) / len(before), sum(after) / len(after)
            out.append({"name": name, "before": round(b, 2), "after": round(a, 2), "change": round((a - b) / b, 3) if b else None,
                        "months_before": len(before), "months_after": len(after)})
    return out
