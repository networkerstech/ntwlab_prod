# -*- coding: utf-8 -*-
from odoo import fields, models, api

from .supply_type import SUPPLY_TYPES

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    hourly_cost = fields.Monetary('Hourly Cost', currency_field='currency_id',
                                  groups="hr.group_hr_user", default=0.0, compute="_compute_costs", store=True, readonly=False)
    daily_cost = fields.Monetary('Daily Cost', currency_field='currency_id',
                                  groups="hr.group_hr_user", default=0.0, compute="_compute_costs", store=True, readonly=False)
    weekly_cost = fields.Monetary('Weekly Cost', currency_field='currency_id',
                                  groups="hr.group_hr_user", default=0.0, compute="_compute_costs", store=True, readonly=False)
    monthly_cost = fields.Monetary('Monthly Cost', currency_field='currency_id',
                                   groups="hr.group_hr_user", default=0.0, readonly=False)
    provider_id = fields.Many2one(comodel_name="res.partner", string="Provider")
    build_ok = fields.Boolean("Can be used in construction")
    supply_type = fields.Selection(
        [item for item in SUPPLY_TYPES.items()],
        string="Supply Type",
        store=True,
        readonly=False
    )

    @api.onchange('build_ok')
    @api.depends('build_ok')
    def _onchange_build_ok(self):
        for rec in self:
            if not rec.build_ok:
                rec.supply_type = False

    @api.depends('monthly_cost')
    def _compute_costs(self):
        for rec in self:
            if rec.monthly_cost:
                # Calcula el costo por semana y por hora basado en el costo por mes
                rec.weekly_cost = rec.monthly_cost / 4  # Aproximadamente 4 semanas al mes
                rec.daily_cost = rec.monthly_cost / 30  # Asumiendo 30 días al mes
                rec.hourly_cost = rec.weekly_cost / 40  # Asumiendo 40 horas por semana
            else:
                # rec los valores si no hay costo por mes
                rec.weekly_cost = 0.0
                rec.daily_cost = 0.0
                rec.hourly_cost = 0.0
