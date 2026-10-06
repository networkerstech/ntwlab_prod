# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

from .supply_type import SUPPLY_TYPES


class BudgetGang(models.Model):
    _name = 'budget.gang'
    _description = 'Gang'

    name = fields.Char(string="Name", required=True)
    employee_ids = fields.Many2many(comodel_name='hr.employee', string="Employees", copy=True)
    line_ids = fields.One2many(comodel_name='budget.gang.line', inverse_name='gang_id', string="Employees", copy=True)
    brigade_chief_id = fields.Many2one(comodel_name='hr.employee', string="Brigade Chief")
    cost_type = fields.Selection(
        selection=[('hour', 'Per hours'), ('day', 'Per Day'), ('week', 'Per Week'), ('month', 'Per Month')],
        string="Cost model",
        required=True,
        default='month'
    )
    percentage = fields.Float(string="Percent (%)", default=0.0)
    brigade_chief_cost = fields.Float(string="Cost Chief", compute="_compute_cost_chief", store=True)
    total_cost = fields.Float(string="Costo Total", compute="_compute_total_cost", store=True)
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Moneda",
        related='company_id.currency_id',
        readonly=True,
        store=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Compañía",
        required=True,
        default=lambda self: self.env.company
    )
    category_id = fields.Many2one(comodel_name="product.category", string="Category")
    internal_reference = fields.Char(string="Internal Reference", copy=False)
    build_ok = fields.Boolean("Can be used in construction")
    supply_type = fields.Selection(
        [item for item in SUPPLY_TYPES.items()],
        string="Supply Type",
        store=True,
        default='work_force',
        readonly=False
    )

    @api.constrains('internal_reference')
    def _check_unique_internal_reference_if_value(self):
        for rec in self:
            if rec.internal_reference:  
                existing = self.search([
                    ('id', '!=', rec.id),
                    ('internal_reference', '=', rec.internal_reference)
                ], limit=1)
                if existing:
                    raise ValidationError("The Internal Reference must be unique")

    def copy(self, default=None):
        default = default or {}
        default.update({"name": f"{self.name} (copy)"})
        res = super(BudgetGang, self).copy(default)
        return res

    @api.onchange('build_ok')
    @api.depends('build_ok')
    def _onchange_build_ok(self):
        for rec in self:
            if not rec.build_ok:
                rec.supply_type = False
            else:
                rec.supply_type = 'work_force'

    @api.onchange( 'brigade_chief_id', 'cost_type', 'percentage')
    @api.depends( 'brigade_chief_id', 'cost_type', 'percentage')
    def _compute_cost_chief(self):
        for rec in self:
            if rec.brigade_chief_id:
                if rec.cost_type == 'hour':
                    rec.brigade_chief_cost = rec.brigade_chief_id.hourly_cost
                elif rec.cost_type == 'week':
                    rec.brigade_chief_cost = rec.brigade_chief_id.weekly_cost
                elif rec.cost_type == 'month':
                    rec.brigade_chief_cost = rec.brigade_chief_id.monthly_cost

    @api.onchange('line_ids', 'line_ids.quantity',  'line_ids.total_cost', 'brigade_chief_id', 'cost_type', 'percentage')
    @api.depends('line_ids', 'line_ids.quantity', 'line_ids.total_cost', 'brigade_chief_id', 'cost_type', 'percentage')
    def _compute_total_cost(self):
        for rec in self:
            total = 0.0
            for line in rec.line_ids:
                total += line.total_cost

            # Sumar el costo del cabo de oficios
            if rec.brigade_chief_id:
                if rec.cost_type == 'hour':
                    total += rec.brigade_chief_id.hourly_cost
                elif rec.cost_type == 'week':
                    total += rec.brigade_chief_id.weekly_cost
                elif rec.cost_type == 'month':
                    total += rec.brigade_chief_id.monthly_cost

            # Aplicar el porcentaje adicional
            if rec.percentage:
                total += total * (rec.percentage / 100.0)

            rec.total_cost = total

class BudgetGangLine(models.Model):
    _name = 'budget.gang.line'
    _description = 'Gang Lines'

    gang_id = fields.Many2one(comodel_name='budget.gang')
    quantity = fields.Integer(string="Quantity")
    employee_id = fields.Many2one(comodel_name='hr.employee', string="Employee", copy=True)
    hourly_cost = fields.Monetary(string='Hourly Cost', currency_field='currency_id', related="employee_id.hourly_cost", store=True, readonly=True)
    daily_cost = fields.Monetary(string='Daily Cost', currency_field='currency_id', related="employee_id.daily_cost", store=True, readonly=True)
    weekly_cost = fields.Monetary(string='Weekly Cost', currency_field='currency_id', related="employee_id.weekly_cost", store=True, readonly=True)
    monthly_cost = fields.Monetary(string='Monthly Cost', currency_field='currency_id', related="employee_id.monthly_cost", store=True, readonly=True)
    total_cost = fields.Monetary(compute="_compute_total_cost", string="Total")
    cost_type = fields.Selection(
        selection=[('hour', 'Per hours'), ('day', 'Per Day'), ('week', 'Per Week'), ('month', 'Per Month')],
        related="gang_id.cost_type",
        string="Cost model"
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Moneda",
        related='gang_id.currency_id',
        readonly=True,
        store=True
    )

    @api.onchange('employee_id', 'cost_type', 'quantity', 'hourly_cost', 'daily_cost', 'weekly_cost', 'monthly_cost')
    @api.depends('employee_id', 'cost_type', 'quantity', 'hourly_cost', 'daily_cost', 'weekly_cost', 'monthly_cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = 0.0
            if rec.cost_type == 'hour':
                rec.total_cost = rec.hourly_cost * rec.quantity
            elif rec.cost_type == 'day':
                rec.total_cost = rec.daily_cost * rec.quantity
            elif rec.cost_type == 'week':
                rec.total_cost = rec.weekly_cost * rec.quantity
            elif rec.cost_type == 'month':
                rec.total_cost = rec.monthly_cost * rec.quantity
