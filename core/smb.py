"""Ten fictional small businesses that use AI tools. Everything here is invented.

Each profile: roles (headcount, hourly cost, task mix), AI tools with monthly seat prices,
how many seats were bought, when the rollout started and how eager the team is.
The generator simulates June-November 2026 day by day for every person.
"""
import math
import random
from datetime import date, timedelta

START, END = date(2026, 6, 1), date(2026, 11, 30)

TOOLS = {  # name: monthly price per seat in EUR (illustrative list prices)
    "ChatGPT Team": 29, "Microsoft 365 Copilot": 28, "Claude Team": 28, "Gemini for Workspace": 20,
    "DeepL Pro": 9, "GitHub Copilot": 18, "Canva AI": 12,
}
MINUTES_SAVED = {"writing": 22, "email": 9, "research": 18, "data": 25, "code": 35, "design": 20,
                 "translation": 15, "customer": 8, "admin": 7}

PROFILES = [
    dict(slug="tax-office", name="Becker & Partner Tax Advisors", industry="Tax advisory", city="Cologne",
         roles=[("Tax advisors", 4, 85, {"research": .4, "writing": .3, "email": .3}),
                ("Accountants", 7, 45, {"data": .5, "email": .3, "admin": .2})],
         tools={"Microsoft 365 Copilot": 11, "DeepL Pro": 3}, start=1, eager=.55),
    dict(slug="dental-practice", name="Dental Practice Dr. Yilmaz", industry="Healthcare", city="Bonn",
         roles=[("Front desk", 5, 32, {"email": .5, "admin": .3, "customer": .2}),
                ("Dentists", 3, 110, {"writing": .6, "research": .4}),
                ("Assistants", 6, 30, {"admin": .7, "email": .3})],
         tools={"ChatGPT Team": 6, "DeepL Pro": 2}, start=3, eager=.4),
    dict(slug="marketing-agency", name="Rheinpixel Marketing Agency", industry="Marketing", city="Düsseldorf",
         roles=[("Content", 7, 48, {"writing": .6, "research": .2, "design": .2}),
                ("Design", 5, 52, {"design": .7, "writing": .3}),
                ("Account management", 6, 55, {"email": .5, "writing": .3, "data": .2})],
         tools={"ChatGPT Team": 18, "Canva AI": 5, "DeepL Pro": 4}, start=0, eager=.9),
    dict(slug="electrician", name="Kaya Electrical Services", industry="Trades", city="Leverkusen",
         roles=[("Office", 4, 35, {"email": .4, "admin": .4, "customer": .2}),
                ("Electricians", 18, 40, {"admin": .6, "research": .4})],
         tools={"ChatGPT Team": 8}, start=4, eager=.3),
    dict(slug="real-estate", name="Lindenthal Real Estate", industry="Real estate", city="Cologne",
         roles=[("Agents", 5, 60, {"writing": .5, "email": .3, "customer": .2}),
                ("Back office", 2, 38, {"admin": .5, "data": .5})],
         tools={"ChatGPT Team": 7}, start=1, eager=.7),
    dict(slug="online-shop", name="Kräuterkiste Online Shop", industry="E-commerce", city="Aachen",
         roles=[("Customer service", 5, 32, {"customer": .6, "email": .4}),
                ("Product & marketing", 4, 45, {"writing": .5, "translation": .3, "design": .2}),
                ("Logistics", 3, 30, {"admin": .7, "data": .3})],
         tools={"ChatGPT Team": 9, "DeepL Pro": 4, "Canva AI": 2}, start=0, eager=.75),
    dict(slug="it-services", name="Nordbyte IT Services", industry="IT services", city="Cologne",
         roles=[("Developers", 12, 70, {"code": .7, "research": .2, "writing": .1}),
                ("Support", 8, 45, {"customer": .5, "research": .3, "email": .2}),
                ("Sales & admin", 5, 50, {"email": .5, "writing": .3, "data": .2})],
         tools={"GitHub Copilot": 12, "Claude Team": 25}, start=0, eager=.85),
    dict(slug="architects", name="Hartmann Architects", industry="Architecture", city="Bonn",
         roles=[("Architects", 7, 65, {"writing": .3, "research": .4, "design": .3}),
                ("Office", 3, 38, {"email": .5, "admin": .5})],
         tools={"Gemini for Workspace": 10}, start=2, eager=.5),
    dict(slug="hotel", name="Hotel am Rheinufer", industry="Hospitality", city="Königswinter",
         roles=[("Reception", 8, 28, {"customer": .5, "email": .3, "translation": .2}),
                ("Sales & events", 4, 42, {"writing": .5, "email": .5}),
                ("Housekeeping & kitchen", 18, 25, {"admin": 1.0})],
         tools={"ChatGPT Team": 12, "DeepL Pro": 4}, start=2, eager=.35),
    dict(slug="law-firm", name="Schulz Labour Law Firm", industry="Legal", city="Cologne",
         roles=[("Lawyers", 6, 120, {"research": .5, "writing": .5}),
                ("Paralegals", 6, 40, {"writing": .4, "admin": .3, "email": .3})],
         tools={"Microsoft 365 Copilot": 12}, start=3, eager=.45),
]

FIRST = ["Anna", "Ben", "Clara", "David", "Elif", "Felix", "Greta", "Hannes", "Ida", "Jonas", "Kira", "Lukas", "Mara",
         "Noah", "Olga", "Paul", "Rana", "Sven", "Tara", "Umut", "Vera", "Yara", "Zoe", "Deniz", "Emil", "Ines", "Jan", "Lea"]
LAST = ["Becker", "Schmitz", "Yilmaz", "Krämer", "Hoffmann", "Nowak", "Wagner", "Kaya", "Schulz", "Richter", "Klein",
        "Wolf", "Neumann", "Braun", "Hartmann", "Lange", "Köhler", "Arslan"]


def _days():
    d = START
    while d <= END:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def _pick(rng, mix):
    r, acc = rng.random(), 0.0
    for k, w in mix.items():
        acc += w
        if r <= acc:
            return k
    return next(iter(mix))


def generate(profile, seed=7):
    rng = random.Random(f"{seed}-{profile['slug']}")
    names = [f"{f} {l}" for f in FIRST for l in LAST]
    rng.shuffle(names)
    tools = list(profile["tools"])
    people, usage = [], []
    for role, count, wage, mix in profile["roles"]:
        for _ in range(count):
            p = {"id": len(people) + 1, "name": names[len(people)], "role": role, "wage": wage, "mix": mix,
                 "eager": rng.random(), "skill": rng.uniform(.4, 1.0), "tools": [],
                 "opt_in": rng.random() > .05}
            people.append(p)
    # hand out each tool's seats to specific people (people can hold several tools)
    for t, n in profile["tools"].items():
        for p in rng.sample(people, min(n, len(people))):
            p["tools"].append(t)
    days = list(_days())
    for p in people:
        uses = bool(p["tools"]) and p["eager"] < profile["eager"] + .1
        begin = START + timedelta(weeks=4 * profile["start"] + int(10 * (1 - p["eager"])))
        n = 0
        for d in days:
            if not uses or d < begin or rng.random() > .6:
                continue
            n += 1
            task = _pick(rng, p["mix"])
            learn = 1 - math.exp(-n / 30)
            minutes = max(2, rng.gauss(MINUTES_SAVED[task], MINUTES_SAVED[task] * .35) * (.5 + .7 * learn) * p["skill"])
            usage.append({"person": p["id"], "day": d.isoformat(), "task": task, "tool": rng.choice(p["tools"]),
                          "minutes_saved": round(minutes, 1), "value_eur": round(minutes / 60 * p["wage"], 2),
                          "corrected": rng.random() < (.3 - .18 * learn) * (1.3 - p["skill"])})
    return people, usage
