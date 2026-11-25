from odoo import fields, models


class AiResult(models.Model):
    _name = "isaiworthit.result"
    _description = "AI results per team and tool"
    _order = "month_id desc, hours_saved desc"

    month_id = fields.Many2one("isaiworthit.month", "Month", required=True, ondelete="cascade", index=True)
    month = fields.Date("Month start", related="month_id.month", store=True)
    department_id = fields.Many2one("hr.department", string="Department",
                                    help="Empty when the team has fewer than 5 people: small teams are combined.")
    team = fields.Char(required=True, help="Team name, or 'Small teams (combined)' / 'Not matched to an employee'.")
    tool_id = fields.Many2one("isaiworthit.tool", "Tool", required=True, ondelete="cascade")
    active_users = fields.Integer("People using AI")
    actions = fields.Float("Counted uses", digits=(16, 0))
    hours_saved = fields.Float("Hours saved", digits=(16, 1))
    value = fields.Monetary("Value of time saved", groups="isaiworthit.group_manager")
    company_id = fields.Many2one(related="month_id.company_id", store=True)
    currency_id = fields.Many2one(related="month_id.currency_id")
