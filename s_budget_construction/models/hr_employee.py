# -*- coding: utf-8 -*-

from odoo import fields, models, api

from .supply_type import SUPPLY_TYPES

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hourly_cost = fields.Monetary('Hourly Cost', currency_field='currency_id',
        groups="hr.group_hr_user", default=0.0, compute="_compute_costs", store=True, readonly=False)
    daily_cost = fields.Monetary('Daily Cost', currency_field='currency_id',
                                  groups="hr.group_hr_user", default=0.0, compute="_compute_costs", store=True, readonly=False)
    weekly_cost = fields.Monetary('Weekly Cost', currency_field='currency_id',
                                  groups="hr.group_hr_user", default=0.0, compute="_compute_costs", store=True, readonly=False)
    monthly_cost = fields.Monetary('Monthly Cost', currency_field='currency_id',
                                  groups="hr.group_hr_user", default=0.0, readonly=False)
    build_ok = fields.Boolean("Can be used in construction")
    category_id = fields.Many2one(comodel_name="product.category", string="Category")
    internal_reference = fields.Char(string="Internal Reference")
    supply_type = fields.Selection(
        [item for item in SUPPLY_TYPES.items()],
        string="Supply Type",
        store=True,
        default='work_force',
        readonly=False
    )

    @api.depends('monthly_cost')
    def _compute_costs(self):
        for employee in self:
            if employee.monthly_cost:
                # Calcula el costo por semana y por hora basado en el costo por mes
                employee.weekly_cost = employee.monthly_cost / 4 # Aproximadamente 4 semanas al mes
                employee.daily_cost = employee.monthly_cost / 30 # Aproximadamente 30 dias al mes
                employee.hourly_cost = employee.weekly_cost / 40  # Asumiendo 40 horas por semana
            else:
                # Resetea los valores si no hay costo por mes
                employee.weekly_cost = 0.0
                employee.daily_cost = 0.0
                employee.hourly_cost = 0.0