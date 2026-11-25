# Connectors

Every connector is optional and off by default. Turn one on in `isaiworthit.config.json` (created by `python3 isaiworthit.py init`), then run `python3 isaiworthit.py sync`. `python3 isaiworthit.py sources` lists them with their status.

**Tested** means run end to end against a local Odoo 18 or real export files. **From docs** means built from the vendor's public API documentation and not yet run against a live account.

## Company data

| Connector | Gives you | How | Status |
|---|---|---|---|
| Odoo | Teams, employees, booked hours, monthly counts of orders, invoices, tickets, deals, tasks | Odoo external API (JSON-RPC) | Tested |
| Team list | Teams and hourly costs | CSV: `user,team,hourly_cost` | Tested |
| Your KPIs | Any monthly number | CSV: `month,name,value` | Tested |
| Licences | Seats and price per tool | Config file | Tested |
| Time-saved survey | Anonymous monthly answers ([how to run it](SURVEY.md)) | CSV from Microsoft Forms or Google Forms | Tested |
| Personio | Employees and departments | Personio API | From docs |

## AI tool usage

| Connector | Gives you | How | Status |
|---|---|---|---|
| Any AI tool | Uses and minutes per person and day | CSV: `date,user,tool,uses,minutes` | Tested |
| Microsoft 365 Copilot | Last day each person used Copilot (anonymised by default) | CSV export from the Microsoft 365 admin center | From docs |
| GitHub Copilot | Daily active users for the organisation | GitHub Copilot metrics API | From docs |
| Claude Code (this computer) | Sessions, active minutes, tools | Local session logs, opt-in per person | Tested |
| Claude Code (whole team) | Per person and day: sessions, lines, commits, PRs | Anthropic Claude Code Analytics API (admin key) | From docs |

Example files for every CSV format are in `examples/`. Secrets (API keys, passwords) are read from environment variables, never from the config file. Names and e-mail addresses are replaced by a salted code before anything is stored.

On the *Data sources* page, a connector that was fed one of the files in `examples/` is marked "sample file".
