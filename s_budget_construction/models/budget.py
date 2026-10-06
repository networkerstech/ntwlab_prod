# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID
from odoo.tools.safe_eval import safe_eval


class BudgetConstruction(models.Model):
    _inherit = "project.project"

    is_budget_construction = fields.Boolean("Is BUdget Construction")

    price_list_id = fields.Many2one(
        string="Price List",
        comodel_name="s.budget.pricelist",
        compute="_compute_pricelist_budget",
        store=True
    )
    total_price = fields.Float(string='Total Price',
        compute="_compute_total_price",)
    percent_to_price = fields.Float(string='Percent to Calculate Price', default=0.0)
    total_cost = fields.Float(
        related='price_list_id.total_cost', store=True)
    
    is_a_buget_template = fields.Boolean("Is A Buget Template", default=False)

    @api.depends('total_cost', 'percent_to_price')
    def _compute_total_price(self):
        for res in self:
            res.total_price = 0
            if res.percent_to_price > 0:
                res.total_price = res.total_cost + ((res.total_cost * res.percent_to_price) / 100)
                
                
    @api.depends('name')
    def _compute_pricelist_budget(self):
        for res in self:
            if res.is_budget_construction:
                if res.price_list_id:
                    res.price_list_id.name = res.name
                else:
                    pricelist = self.env["s.budget.pricelist"].with_user(
                        SUPERUSER_ID).search([('id_budget', '=', res._origin.id)])
                    if not pricelist:
                        pricelist = self.env["s.budget.pricelist"].with_user(SUPERUSER_ID).create(
                            {'name': res.name, 'id_budget': res._origin.id, 'is_a_buget_template': res.is_a_buget_template})
                    pricelist.name = res.name
                    res.price_list_id = pricelist.id
            else:
                res.price_list_id = False

    def action_open_budget(self):
        """
        Usar este action desde un action server con código, para que al recargar
        la página se vuelva a ejecutar
            action = model.action_open_budget()
        """
        action_dict = self.env.ref(
            "s_budget_construction.budget_item_hierarchical_action"
        ).read()[0]
        # Se establece el id del server action para que en el reload se vuelva a llamar este método
        action_dict.update(
            {"id": self.env.ref(
                "s_budget_construction.budged_action_server").id}
        )
        default_is_budget_construction = self.env.context.get('default_is_budget_construction', False)
        new_context = dict(self.env.context or {})
        active_id = new_context.get('active_id', False)

        if not "active_model" in new_context:
            # Se establece el active model a projet.project porque en el reload se pierde
            new_context.update({"active_model": "project.project"})
        action_ctx = safe_eval(action_dict.get("context", "{}"))
        new_context.update(action_ctx)

        pjct = self
        if not self and active_id:
            pjct = self.env['project.project'].browse(new_context['active_id'])

        if default_is_budget_construction or not pjct.is_a_buget_template:
            new_context.update(dict(is_template=False))
        else:
            new_context.update(dict(is_template=True))
        action_dict["name"] = pjct.name if pjct.name else ''
        action_dict["display_name"] = pjct.name if pjct.name else ''
        action_dict["context"] = new_context
        if not default_is_budget_construction and pjct.is_a_buget_template:
            action_dict["domain"] = "[('is_a_buget_template', '=', True)]"

        return action_dict
