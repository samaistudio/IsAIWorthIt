# The one-question time-saved survey

Benchmarks are averages. A short monthly survey tells IsAIWorthIt how much time *your* team actually saves, and the benchmark estimate is adjusted to match. It takes each person ten seconds.

## The question

> **About how much time did AI tools save you this week?**
>
> - None
> - Less than 1 hour
> - 1–3 hours
> - 3–5 hours
> - More than 5 hours

Optional second field: **Team** (a dropdown with your team names). Leave it out if your teams are small – IsAIWorthIt never shows results for fewer than 5 people anyway.

Do **not** ask for names or e-mail addresses. Turn off "record name" / "collect e-mail" in the form settings.

## Set it up

**Microsoft Forms:** New form → add a *Choice* question with the text and answers above → Settings → *Anyone can respond* or *Only people in my organisation* with **Record name switched off** → share the link in Teams once a month.

**Google Forms:** New form → *Multiple choice* question → Settings → Responses → **Collect email addresses: Off** → send the link once a month.

## Import the answers

1. Export the responses as CSV (Microsoft Forms: *Open in Excel* → save as CSV; Google Forms: Responses → *Download responses (.csv)*).
2. Rename the columns to `month`, `answer` and, if you used it, `team`. `month` is the month the answers belong to, written `2026-11`.
3. In `isaiworthit.config.json`, switch on `survey_csv` and list the file. Run `python3 isaiworthit.py sync`.

Numbers also work as answers (`2` or `1.5` = hours per week).

## How the answers are used

- IsAIWorthIt takes the **median** answer, so one person who writes "more than 5 hours" cannot skew the result.
- It is converted to hours per month (× 4.33) and compared with the benchmark estimate for the people who used AI that month.
- The benchmarks are then scaled by that ratio – but never more than 4× up or down. If the gap is that large, the dashboard tells you to check the benchmark values.
- With fewer than 5 answers in a month, the survey is ignored and the benchmark estimate is shown.
