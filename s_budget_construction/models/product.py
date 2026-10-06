# -*- coding: utf-8 -*-

from odoo import models, fields, api

from .supply_type import SUPPLY_TYPES


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _rec_name = 'name'

    build_ok = fields.Boolean("Can be used in construction")
    tool_ok = fields.Boolean("Tool")
    machinery_ok = fields.Boolean("Machinery")
    supply_type_id = fields.Many2one(
        compute="_compute_supply_type_id",
        store=True,
        comodel_name= "s.budget.const.supply.type",
        string="Supply type",
    )
    supply_type = fields.Selection(
        [item for item in SUPPLY_TYPES.items()],
        string="Supply type",
    )
    use_percent = fields.Float(string="Percentage of use")

    @api.onchange('supply_type_id')
    @api.depends('supply_type')
    def _compute_supply_type_id(self):
        for rec in self:
            if rec.supply_type:
                domain = [('supply_type', '=', rec.supply_type)]
                supply_type_id = self.env['s.budget.const.supply.type'].search(domain, limit=1)
                rec.supply_type_id = supply_type_id if supply_type_id else False
            else:
                rec.supply_type_id = False

    @api.onchange('tool_ok', 'machinery_ok')
    def _onchange_tool(self):
        for rec in self:
            if rec.tool_ok or rec.machinery_ok:
                rec.build_ok = True