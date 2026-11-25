from odoo import api, fields, models


class AiMonth(models.Model):
    _name = "isaiworthit.month"
    _description = "AI results per month"
    _order = "month desc"
    _rec_name = "label"

    month = fields.Date("Month", required=True, help="First day of the month.")
    label = fields.Char(compute="_compute_label", store=True)
    active_users = fields.Integer("People using AI")
    benchmark_hours = fields.Float("Hours (benchmark)", digits=(16, 1))
    survey_answers = fields.Integer("Survey answers")
    calibration_factor = fields.Float("Calibration factor", digits=(16, 2), default=1.0,
                                      help="Survey median ÷ benchmark per person. Only used with 5 or more answers, limited to 0.25–4.")
    hours_saved = fields.Float("Hours saved", digits=(16, 1))
    hourly_cost = fields.Monetary("Hourly cost", groups="isaiworthit.group_manager")
    value = fields.Monetary("Value of time saved", groups="isaiworthit.group_manager")
    licence_cost = fields.Monetary("Licence costs", groups="isaiworthit.group_manager",
                                   help="Seats × price per seat as set under AI licences at the time of the import. "
                                        "Past months use today's prices when they are imported again.")
    net = fields.Monetary("Net benefit", compute="_compute_net", store=True, groups="isaiworthit.group_manager")
    result_ids = fields.One2many("isaiworthit.result", "month_id", string="By team and tool")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related="company_id.currency_id")

    _sql_constraints = [("month_company_uniq", "unique(month, company_id)", "This month was already imported.")]

    @api.depends("month")
    def _compute_label(self):
        for m in self:
            m.label = m.month.strftime("%Y-%m") if m.month else False

    @api.depends("value", "licence_cost")
    def _compute_net(self):
        for m in self:
            m.net = m.value - m.licence_cost
