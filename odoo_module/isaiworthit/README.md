# IsAIWorthIt for Odoo 18

An Odoo 18 app that shows what a company's AI tools save (hours and euros) and what the licences cost, per month and per department. Nothing is stored per person.

- **Import usage**: a CSV with `date, user, tool, uses, minutes` (comma or semicolon, UTF-8 or Windows-1252), plus an optional anonymous monthly survey (`month, answer`).
- **Results**: one row per month (value of time saved, licence costs, net benefit) and a pivot per department and tool.
- **Access**: *Viewer* sees hours per team. *Manager* also sees money, licences and the import. Record rules keep each company's data separate.

Depends only on `hr` (Employees). Built for Odoo 18 and tested on Odoo 18 Community.

Translations: `i18n/isaiworthit.pot` (template) and `i18n/de.po` (German). Load German under *Settings → Languages*; labels such as "Hours saved" then read "Eingesparte Stunden".

## Install

Copy this folder into your add-ons path, update the apps list and install **IsAIWorthIt**. To try it with Docker, see the repository README.

Tests: `odoo -d <test-db> -i isaiworthit --test-enable --test-tags /isaiworthit --stop-after-init`

## Known limits

- Departments with fewer than 5 employees are combined into "Small teams (combined)". The rule counts the employees in a department, not the people who used one tool, so a single tool in a department can still show a row for one or two people.
- Users not matched to an employee are grouped as one row regardless of size; keep the usage file to employees.
- Licence costs come from the seats and prices under *AI licences* at the time of the import, also for past months.
- Departments are matched by name, so two departments with the same name are counted as one team.

## License

License: Apache-2.0 (SPDX: Apache-2.0). Odoo's manifest has no Apache value, so `__manifest__.py` declares it as `"Other OSI approved licence"`. Full text: `LICENSE` in the repository root.

Author: Sam Zeidi
