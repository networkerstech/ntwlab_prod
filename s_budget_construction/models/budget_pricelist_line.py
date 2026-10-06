# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class BudgetPricelistLine(models.Model):
    _name = "s.budget.pricelist.line"
    _description = "Pricelist Line"
    _rec_name = "supply_id"

    _sql_constraints = [
        ('name_uniq', "unique(price_list_id, supply_id)", "This Priceline is duplicated")]

    price_list_id = fields.Many2one(
        string="Price List",
        comodel_name="s.budget.pricelist",
    )
    supply_code = fields.Char(
        "Code",
        related="supply_id.code",
        readonly=False,
        store=False,
    )
    supply_id = fields.Many2one(
        string="Suply",
        comodel_name="s.budget.const.supply",
    )
    supply_type = fields.Selection(
        related="supply_id.supply_type", store=True, readonly=True
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="price_list_id.currency_id", store=True)
    uom_supply_id = fields.Many2one(
        "uom.uom", related="supply_id.uom_id", store=True)
    uom_id = fields.Many2one("uom.uom", string="Unit")
    quantity = fields.Float(string="Quantity", default=1, digits=(16, 7))
    price = fields.Float(string="Price")
    quantity_used = fields.Float(
        string="Quantity Used", default=0, digits=(16, 7), store=True)
    price_total = fields.Float(string="Price Total", store=True)

    component_tools_ids = fields.One2many(
        "s.budget.const.concept.component",
        "pricelist_line_id",
        "Componets",
        copy=False,
    )

    def _set_price_total(self):
        for rec in self:
            components = []
            cant = 0
            for cmp in rec.component_tools_ids:
                id_con, quantity = rec._calcule_concept_quantity(cmp)
                components.append({'id': id_con, 'quantity': quantity})
            for com in components:
                for tsk in com['id'].tasks_ids:
                    cant += com['quantity'] * rec._calcule_tasks_quantity(tsk)
            rec.quantity_used = cant
            rec.price_total = rec.quantity_used * rec.price

    def _calcule_concept_quantity(self, component_id):
        sly_qty = component_id.quantity
        if component_id.supply_id and component_id.supply_id.id == self.supply_id.id:
            converted_qty = self.uom_id._compute_quantity(
                sly_qty, component_id.uom_id)
            sly_qty = converted_qty
        if component_id.parent_id:
            id_con, quantity = self._calcule_concept_quantity(
                component_id.parent_id)
            return id_con, quantity * sly_qty
        if component_id.concept_id:
            return component_id.concept_id, sly_qty
        return False, 0

    def _calcule_tasks_quantity(self, task):
        sly_qty = task.budget_qty
        if task.parent_id:
            return sly_qty * self._calcule_tasks_quantity(task.parent_id)
        return sly_qty

    @api.onchange('supply_id')
    def _onchange_uom_supply_id(self):
        for res in self:
            res.uom_id = res.uom_supply_id
