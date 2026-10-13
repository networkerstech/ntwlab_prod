# -*- coding: utf-8 -*-
# author: Gonscar88
# create_date: 2026-10-12
# project: networkers-odoo-lab

from odoo import models, fields, api, _, SUPERUSER_ID, Command
from odoo.exceptions import UserError
from odoo.orm.identifiers import NewId

from .supply_type import SUPPLY_TYPES


class BudgetConcept(models.Model):
    _name = "s.budget.const.concept"
    _description = "Concept"
    _rec_name = "code"

    _budget_code_unique_by_project = models.Constraint(
        "unique (code, project_id)",
        "Concept code must be unique by budget.",
    )

    concept_template_id = fields.Many2one(
        "s.budget.const.concept", string="Concept Template"
    )

    code = fields.Char("Code", required=True)
    name = fields.Char("Name", required=True)
    description = fields.Text("Description", required=True, translate=True)
    uom_id = fields.Many2one("uom.uom", "UM")
    price_unit = fields.Float("Price unit")
    price_unit_aux = fields.Float("Price unit", compute="_set_pricelist_line_id")
    project_id = fields.Many2one(
        "project.project", string="Project", ondelete="cascade"
    )

    is_a_buget_template = fields.Boolean(
        related="project_id.is_a_buget_template", store=True
    )
    tasks_ids = fields.One2many(
        "project.task",
        "concept_id",
        "Tasks",
        copy=False,
    )

    price_list_id = fields.Many2one(
        comodel_name="s.budget.pricelist",
        related="project_id.price_list_id",
        store=True,
        copy=False,
    )

    component_ids = fields.One2many(
        "s.budget.const.concept.component", "concept_id", "Componets"
    )

    component_material_ids = fields.One2many(
        "s.budget.const.concept.component",
        "concept_id",
        "Componets",
        copy=False,
        domain=[("supply_type", "=", "material")],
    )
    component_work_force_ids = fields.One2many(
        "s.budget.const.concept.component",
        "concept_id",
        "Work force componets",
        domain=[("supply_type", "=", "work_force")],
        copy=False,
    )
    component_tools_ids = fields.One2many(
        "s.budget.const.concept.component",
        "concept_id",
        "Tools componets",
        domain=[("supply_type", "=", "tools")],
        copy=False,
    )
    component_machinery_ids = fields.One2many(
        "s.budget.const.concept.component",
        "concept_id",
        "Machinery componets",
        domain=[("supply_type", "=", "machinery")],
        copy=False,
    )
    component_auxiliaries_ids = fields.One2many(
        "s.budget.const.concept.component",
        "concept_id",
        "Auxiliaries components",
        domain=[("supply_type", "=", "auxiliaries")],
        copy=False,
    )
    component_transport_cost_ids = fields.One2many(
        "s.budget.const.concept.component",
        "concept_id",
        "Transport cost componets",
        domain=[("supply_type", "=", "transport_cost")],
        copy=False,
    )

    @api.depends("component_ids", "component_ids.price_total")
    def _set_pricelist_line_id(self):
        for rec in self:
            rec.price_unit = 0
            rec.price_unit_aux = 0
            for r in rec.component_ids:
                rec.price_unit += r.price_total
                rec.price_unit_aux += r.price_total

    def set_template_element(self):
        self.action_save_and_stay()
        proj = self.env["project.project"].search(
            [("is_a_buget_template", "=", True), ("is_budget_construction", "=", True)]
        )
        for pj in proj:
            for res in self:
                default = {
                    "project_id": pj.id,
                    "price_list_id": pj.price_list_id.id,
                    "price_unit": 0,
                }
                concept = res.copy(default)
                res.concept_template_id = concept.id
                if res.tasks_ids:
                    default = {
                        "project_id": pj.id,
                        "concept_id": concept.id,
                        "parent_id": False,
                        "name": res.name,
                    }
                    res.tasks_ids[0].copy(default)

    def write(self, vals):
        if "name" in vals:
            for record in self:
                tasks = self.env["project.task"].search(
                    [("concept_id", "=", record.id)]
                )
                tasks.with_context(change_in_concept=True).write(
                    {"name": vals.get("name")}
                )
        return super().write(vals)

    def copy(self, default=None):
        self.ensure_one()
        copied_record = super(BudgetConcept, self).copy(default)
        if self.env.context.get("no_chield_copy", True):
            self._copy_children(copied_record)
        return copied_record

    def _copy_children(self, copied_concept):
        for child in self.component_ids:
            child_default = {
                "concept_id": copied_concept.id,
            }
            copied_child = child.copy(child_default)
            child._set_price_list_line_id()
            child._copy_children(copied_child)

    def action_save_and_stay(self):
        for record in self:
            component_ids = record.component_ids | record.component_ids.mapped('component_ids')
            for component in component_ids:
                if not component.supply_id:
                    codigo = (
                        component.supply_code_aux
                        or component.product_template_id.default_code
                        or component.budget_gang_id.internal_reference
                        or component.fleet_vehicle_id.license_plate
                    )
                    if not codigo:
                        raise UserError(_(
                            "The component %s has no code. Set a code on the component "
                            "or an internal reference on its product, gang or vehicle.",
                            component.description,
                        ))
                    if not component.supply_code_aux:
                        component.supply_code_aux = codigo
                    supply = self.env["s.budget.const.supply"].search(
                        [
                            ("code", "=", codigo),
                            ("project_id", "=", record.project_id.id),
                        ],
                        limit=1,
                    )
                    if not supply:
                        supply_type_id = self.env["s.budget.const.supply.type"].search(
                            [("supply_type", "=", component.supply_type)], limit=1
                        )
                        new_supply = self.env["s.budget.const.supply"].create(
                            {
                                "code": codigo,
                                "description": component.description,
                                "uom_id": component.uom_id.id,
                                "price_unit": component.price_unit,
                                "supply_type_id": supply_type_id.id,
                                "product_template_id": component.product_template_id.id,
                                "budget_gang_id": component.budget_gang_id.id,
                                "fleet_vehicle_id": component.fleet_vehicle_id.id,
                                "project_id": record.project_id.id,
                            }
                        )
                        component.supply_id = new_supply.id
                        component.description = new_supply.description
                        component.uom_id = new_supply.uom_id
                        component.price_unit = new_supply.price_unit
                    else:
                        component.write({'supply_id': supply.id})

        action = {
            "type": "ir.actions.act_window",
            "name": _("Concept"),
            "res_model": "s.budget.const.concept",
            "res_id": self.id,
            "views": [
                (
                    self.env.ref("s_budget_construction.budget_concept_view_form").id,
                    "form",
                )
            ],
            "target": "new",
        }
        return action

    @api.onchange("component_auxiliaries_ids")
    def _onchange_supply_id(self):
        for record in self:
            for ca in record.component_auxiliaries_ids:
                if ca.supply_id.component_ids:
                    ca.component_ids = [Command.clear()]
                    component_vals = []
                    for supply_component in ca.supply_id.component_ids:
                        component_vals.append(
                            Command.create(
                                {
                                    "parent_id": ca.id.origin,
                                    "product_template_id": supply_component.product_template_id.id,
                                    "fleet_vehicle_id": supply_component.fleet_vehicle_id.id,
                                    "budget_gang_id": supply_component.budget_gang_id.id,
                                    "supply_code_aux": supply_component.supply_code_aux,
                                    "supply_code": supply_component.supply_code,
                                    "supply_id": supply_component.supply_id.id,
                                    "supply_type": supply_component.supply_type,
                                    "description": supply_component.description,
                                    "uom_id": supply_component.uom_id.id,
                                    "quantity": supply_component.quantity,
                                }
                            )
                        )
                    ca.component_ids = component_vals



