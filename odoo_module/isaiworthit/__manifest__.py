{
    "name": "IsAIWorthIt – AI cost vs. time saved",
    "summary": "See what your team's AI tools cost and how much time they save, per month and per department. No tracking of individuals.",
    "version": "18.0.0.2.0",
    "category": "Human Resources",
    "author": "Sam Zeidi",
    "website": "https://github.com/samaistudio/IsAIWorthIt",
    # Apache-2.0 (SPDX: Apache-2.0). Odoo's manifest has no Apache value, so it is declared as
    # "Other OSI approved licence"; see README.md and LICENSE in the repository root.
    "license": "Other OSI approved licence",
    "depends": ["hr"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/tools.xml",
        "views/month_views.xml",
        "views/result_views.xml",
        "views/tool_views.xml",
        "wizard/import_views.xml",
        "views/menus.xml",
    ],
    "images": ["static/description/banner.png"],
    "application": True,
    "installable": True,
}
