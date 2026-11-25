from odoo import api, fields, models


class AiTool(models.Model):
    _name = "isaiworthit.tool"
    _description = "AI tool licence"
    _order = "monthly_cost desc, name"

    name = fields.Char(required=True)
    seats = fields.Integer(help="Paid seats / licences.")
    cost_per_seat = fields.Monetary("Cost per seat", help="Price per seat and month.", groups="isaiworthit.group_manager")
    monthly_cost = fields.Monetary("Monthly cost", compute="_compute_cost", store=True, groups="isaiworthit.group_manager")
    unit = fields.Selection([("use", "Per use"), ("session", "Per session"), ("active_day", "Per active day")],
                            default="use", required=True,
                            help="What one counted activity in the usage file means for this tool.")
    minutes_per_action = fields.Float("Min. per use", default=5.0, help="Benchmark: minutes saved per counted activity. A starting point; "
                                                        "the monthly staff survey corrects it.")
    active_users = fields.Integer("Active", compute="_compute_usage", help="People who used the tool in the latest imported month.")
    unused_seats = fields.Integer("Unused", compute="_compute_usage")
    unused_cost = fields.Monetary("Unused seats cost", compute="_compute_usage", groups="isaiworthit.group_manager")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related="company_id.currency_id")

    _sql_constraints = [("name_company_uniq", "unique(name, company_id)", "This AI tool already exists.")]

    @api.depends("seats", "cost_per_seat")
    def _compute_cost(self):
        for t in self:
            t.monthly_cost = t.seats * t.cost_per_seat

    def _compute_usage(self):
        Month = self.env["isaiworthit.month"].sudo()
        for t in self:
            last = Month.search([("company_id", "=", t.company_id.id)], order="month desc", limit=1)
            used = sum(last.result_ids.filtered(lambda r: r.tool_id == t).mapped("active_users")) if last else 0
            t.active_users = used
            t.unused_seats = max(0, t.seats - used)
            t.sudo().unused_cost = t.unused_seats * t.sudo().cost_per_seat
