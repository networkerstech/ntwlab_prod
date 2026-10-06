# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BudgetPricelist(models.Model):
    _name = "s.budget.pricelist"
    _description = "Pricelist"

    name = fields.Char(string="Name", copy=False)
    id_budget = fields.Char(string="Id Budget", copy=False)

    is_a_buget_template = fields.Boolean("Is A Buget Template", default=False)

    pricelist_line_ids = fields.One2many(
        string="Pricelist Lines",
        comodel_name="s.budget.pricelist.line",
        inverse_name="price_list_id",
        copy=False
    ) 
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost')

    @api.depends('pricelist_line_ids.price_total')
    def _compute_total_cost(self):
        for record in self:
            total = sum(line.price_total for line in record.pricelist_line_ids)
            record.total_cost = total
            
    pricelist_material_ids = fields.One2many(
        "s.budget.pricelist.line",
        "price_list_id",
        "Componets",
        domain=[('supply_type', '=', 'material')],
        copy=False,
    )
    pricelist_work_force_ids = fields.One2many(
        "s.budget.pricelist.line",
        "price_list_id",
        "Work force componets",
        domain=[('supply_type', '=', 'work_force')],
        copy=False,
    )
    pricelist_tools_ids = fields.One2many(
        "s.budget.pricelist.line",
        "price_list_id",
        "Tools componets",
        domain=[('supply_type', '=', 'tools')],
        copy=False,
    )
    pricelist_machinery_ids = fields.One2many(
        "s.budget.pricelist.line",
        "price_list_id",
        "Machinery componets",
        domain=[('supply_type', '=', 'machinery')],
        copy=False,
    )
    pricelist_auxiliaries_ids = fields.One2many(
        "s.budget.pricelist.line",
        "price_list_id",
        "Auxiliaries componets",
        domain=[('supply_type', '=', 'auxiliaries')],
        copy=False,
    )
    pricelist_transport_cost_ids = fields.One2many(
        "s.budget.pricelist.line",
        "price_list_id",
        "Transport cost componets",
        domain=[('supply_type', '=', 'transport_cost')],
        copy=False,
    )
    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        copy=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        string="Currency",
        comodel_name="res.currency",
        copy=True,
        default=lambda self: self.env.company.currency_id
    )

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        for res in self.mapped('pricelist_line_ids'):
            res._onchange_supply_id()

    def set_price_total(self):
        for rec in self:
            rec.pricelist_line_ids._set_price_total()
            for pli in rec.pricelist_line_ids:
                if not pli.component_tools_ids:
                    pli.unlink()
