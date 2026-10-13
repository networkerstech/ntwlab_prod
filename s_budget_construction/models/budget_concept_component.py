# -*- coding: utf-8 -*-
# author: Gonscar88
# create_date: 2026-10-12
# project: networkers-odoo-lab

from odoo import models, fields, api, _, SUPERUSER_ID, Command
from odoo.exceptions import UserError
from odoo.orm.identifiers import NewId

from .supply_type import SUPPLY_TYPES
class BudgetConceptComponent(models.Model):
    _name = "s.budget.const.concept.component"
    _description = "Construction budget componet line"

    proj_id = fields.Char("Proyecto")
    concept_code = fields.Char("Concepto")
    parent_code = fields.Char("Parent")
    concept_id = fields.Many2one("s.budget.const.concept", string="Concept")
    product_template_id = fields.Many2one(
        comodel_name="product.template", string="Producto", domain=[('build_ok', '=', True)]
    )
    project_id = fields.Many2one(
        'project.project', string="Proyecto relacionado", related='concept_id.project_id', store=True, readonly=False
    )
    fleet_vehicle_id = fields.Many2one(comodel_name="fleet.vehicle", string="Vehicle")
    budget_gang_id = fields.Many2one(comodel_name="budget.gang", string="Gang")

    concept_price_list_id = fields.Many2one(
        comodel_name="s.budget.pricelist",
        related="concept_id.price_list_id",
        store=True,
    )

    price_list_id = fields.Many2one(
        comodel_name="s.budget.pricelist", compute="_set_pricelist_id", store=True
    )

    supply_code_aux = fields.Char(
        "Código producto",
    )
    supply_code = fields.Char(
        "Código de Supply",
        related="supply_id.code",
        readonly=False,
        store=True,
    )
    name = fields.Char(
        "Nombre",
        compute="_compute_name",
        store=True,
        help="Código del insumo, nombre del producto y nombre del proyecto separados por ' - '",
    )

    def _get_default_supply_type(self):
        supply_type = None
        if self.env.context.get("is_material", False):
            supply_type = "material"
        if self.env.context.get("is_work_force", False):
            supply_type = "work_force"
        if self.env.context.get("is_tools", False):
            supply_type = "tools"
        if self.env.context.get("is_machinery", False):
            supply_type = "machinery"
        if self.env.context.get("is_transport_cost", False):
            supply_type = "transport_cost"
        return supply_type

    supply_id = fields.Many2one(
        "s.budget.const.supply", string="Supply", store=True,
        help="Conjunto compuesto de materiales/herramientas y otros. Si ya existe en el catálogo se precargarán precios"
    )

    supply_type = fields.Selection(
        [item for item in SUPPLY_TYPES.items()], default=_get_default_supply_type
    )
    description = fields.Char("Description")
    price_unit = fields.Float("Price unit", compute="_set_pricelist_price_unit", store=True, readonly=False)
    uom_id = fields.Many2one("uom.uom", "UM")
    quantity = fields.Float("Quantity", digits=(16, 7))
    price_total = fields.Float("Price total", compute="_set_price_total")

    parent_id = fields.Many2one("s.budget.const.concept.component", string="Parent")
    component_ids = fields.One2many(
        "s.budget.const.concept.component", "parent_id", "Componets"
    )
    component_material_ids = fields.One2many(
        "s.budget.const.concept.component",
        "parent_id",
        "Componets",
        domain=[("supply_type", "=", "material")],
        copy=False,
    )
    component_work_force_ids = fields.One2many(
        "s.budget.const.concept.component",
        "parent_id",
        "Work force componets",
        domain=[("supply_type", "=", "work_force")],
        copy=False,
    )
    component_tools_ids = fields.One2many(
        "s.budget.const.concept.component",
        "parent_id",
        "Tools componets",
        domain=[("supply_type", "=", "tools")],
        copy=False,
    )
    component_machinery_ids = fields.One2many(
        "s.budget.const.concept.component",
        "parent_id",
        "Machinery componets",
        domain=[("supply_type", "=", "machinery")],
        copy=False,
    )
    component_auxiliaries_ids = fields.One2many(
        "s.budget.const.concept.component",
        "parent_id",
        "Auxiliaries componets",
        domain=[("supply_type", "=", "auxiliaries")],
        copy=False,
    )
    component_transport_cost_ids = fields.One2many(
        "s.budget.const.concept.component",
        "parent_id",
        "Transport cost componets",
        domain=[("supply_type", "=", "transport_cost")],
        copy=False,
    )
    pricelist_line_id = fields.Many2one(
        comodel_name="s.budget.pricelist.line",
        string="Pricelist Line",
        store=True,
        compute="_set_price_list_line_id",
    )

    @api.depends("supply_code_aux", "product_template_id.name", "proj_id")
    def _compute_name(self):
        """Arma el nombre visible del componente con las partes que estén establecidas."""
        for record in self:
            partes = [record.supply_code_aux, record.product_template_id.name, record.project_id.name]
            record.name = " - ".join(parte for parte in partes if parte)

    @api.onchange("supply_code_aux")
    def _onchange_supply_code(self):
        if self.supply_code_aux:
            supply = self.env["s.budget.const.supply"].search(
                [
                    ("code", "=", self.supply_code_aux),
                    ("project_id", "=", self.project_id)
                ],
                limit=1,
            )
            if supply:
                self.supply_id = supply
                self.supply_type = supply.supply_type
                self.description = supply.description
                self.uom_id = supply.uom_id
                self.product_template_id = supply.product_template_id
                self.budget_gang_id = supply.budget_gang_id
                self.fleet_vehicle_id = supply.fleet_vehicle_id
            else:
                if self.env.context.get("is_all", False) or self.supply_type == False:
                    product_id = self.env["product.template"].search(
                        [
                            ("default_code", "=", self.supply_code_aux),
                            ("build_ok", "=", True),
                        ],
                        limit=1,
                    )
                    if product_id:
                        self.product_template_id = product_id
                        self.description = product_id.name
                        self.uom_id = product_id.uom_id
                    else:
                        budget_gang_id = self.env["budget.gang"].search(
                            [
                                ("internal_reference", "=", self.supply_code_aux),
                                ("build_ok", "=", True),
                            ],
                            limit=1,
                        )
                        if budget_gang_id:
                            self.budget_gang_id = budget_gang_id
                            self.description = budget_gang_id.name

                elif (
                        self.env.context.get("is_material", False)
                        or self.supply_type == "material"
                ):
                    self.supply_type = "material"
                    product_id = self.env["product.template"].search(
                        [
                            ("default_code", "=", self.supply_code_aux),
                            ("supply_type", "=", "material"),
                            ("build_ok", "=", True),
                        ],
                        limit=1,
                    )
                    if product_id:
                        self.product_template_id = product_id
                        self.description = product_id.name
                        self.uom_id = product_id.uom_id
                elif (
                        self.env.context.get("is_work_force", False)
                        or self.supply_type == "work_force"
                ):
                    self.supply_type = "work_force"
                    budget_gang_id = self.env["budget.gang"].search(
                        [
                            ("build_ok", "=", True),
                            ("internal_reference", "=", self.supply_code_aux),
                            ("supply_type", "=", "work_force"),
                        ],
                        limit=1,
                    )
                    if budget_gang_id:
                        self.budget_gang_id = budget_gang_id
                        self.description = budget_gang_id.name
                elif (
                        self.env.context.get("is_tools", False)
                        or self.supply_type == "tools"
                ):
                    self.supply_type = "tools"
                    product_id = self.env["product.template"].search(
                        [
                            ("default_code", "=", self.supply_code_aux),
                            ("supply_type", "=", "tools"),
                            ("build_ok", "=", True),
                        ],
                        limit=1,
                    )
                    if product_id:
                        self.product_template_id = product_id
                        self.description = product_id.name
                        self.uom_id = product_id.uom_id
                elif (
                        self.env.context.get("is_machinery", False)
                        or self.supply_type == "machinery"
                ):
                    self.supply_type = "machinery"
                    product_id = self.env["product.template"].search(
                        [
                            ("default_code", "=", self.supply_code_aux),
                            ("supply_type", "=", "machinery"),
                            ("build_ok", "=", True),
                        ],
                        limit=1,
                    )
                    if product_id:
                        self.product_template_id = product_id
                        self.description = product_id.name
                        self.uom_id = product_id.uom_id
                elif (
                        self.env.context.get("is_transport_cost", False)
                        or self.supply_type == "transport_cost"
                ):
                    self.supply_type = "transport_cost"
                    vehicle_id = self.env["fleet.vehicle"].search(
                        [
                            ("license_plate", "=", self.supply_code_aux),
                            ("supply_type", "=", "transport_cost"),
                            ("build_ok", "=", True),
                        ],
                        limit=1,
                    )
                    if vehicle_id:
                        self.fleet_vehicle_id = vehicle_id

    @api.onchange("product_template_id")
    def _onchange_product_template_id(self):
        if self.product_template_id:
            self.product_template_id = self.product_template_id
            self.description = self.product_template_id.name
            self.uom_id = self.product_template_id.uom_id
            self.supply_code_aux = self.product_template_id.default_code
            self.supply_type = (
                self.product_template_id.supply_type
                if not self.supply_type
                else self.supply_type
            )

    @api.onchange("budget_gang_id")
    def _onchange_budget_gang_id(self):
        if self.budget_gang_id:
            self.budget_gang_id = self.budget_gang_id
            self.description = self.budget_gang_id.name
            self.supply_type = (
                self.budget_gang_id.supply_type
                if not self.supply_type
                else self.supply_type
            )

    @api.onchange("fleet_vehicle_id")
    def _onchange_fleet_vehicle_id(self):
        if self.fleet_vehicle_id:
            self.fleet_vehicle_id = self.fleet_vehicle_id
            self.description = self.fleet_vehicle_id.name
            self.supply_type = (
                self.fleet_vehicle_id.supply_type
                if not self.supply_type
                else self.supply_type
            )

    @api.depends("concept_price_list_id", "parent_id")
    def _set_pricelist_id(self):
        for rec in self:
            if rec.concept_price_list_id:
                rec.price_list_id = rec.concept_price_list_id.id
            if rec.parent_id:
                rec.parent_id._set_pricelist_id()
                rec.price_list_id = rec.parent_id.price_list_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if val.get("proj_id", False):

                if val.get("supply_code_aux", False):
                    supply = self.env["s.budget.const.supply"].search(
                        [
                            ("code_suply", "=", val.get("supply_code_aux", False)),
                        ],
                        limit=1,
                    )
                    if supply:
                        val.update({"supply_id": supply.id})
                concept = self.env["s.budget.const.concept"].search(
                    [
                        ("code", "=", val.get("concept_code", False)),
                        ("project_id", "=", int(val.get("proj_id", False))),
                    ],
                    limit=1,
                )
                if concept and not val.get("parent_code", False):
                    val.update({"concept_id": concept.id})
                if concept and val.get("parent_code", False):
                    for r in concept.component_ids:
                        if r.supply_code == val.get("parent_code", False):
                            val.update({"parent_id": r.id})
                        part = r.search_component(
                            r.component_ids, val.get("parent_code", False)
                        )
                        if part:
                            val.update({"parent_id": part})
        res = super().create(vals_list)
        for rec in res:
            if rec.supply_type == 'auxiliaries':
                auxiliar = self.env['s.budget.const.concept.component'].search(
                    [
                        ('supply_code', '=', rec.supply_code_aux),
                    ],
                    limit=1
                )
                if auxiliar:
                    for comp in auxiliar.component_ids:
                        values = comp.copy_data()[0]
                        values['parent_id'] = rec.id
                        self.env['s.budget.const.concept.component'].create(values)
        return res

    def search_component(self, compo, code):
        for r in compo:
            if r.supply_code == code:
                return r.id
        return False

    @api.depends("price_list_id", "supply_id", "product_template_id")
    def _set_price_list_line_id(self):
        lineas_por_lista_e_insumo = {
            (linea.price_list_id.id, linea.supply_id.id): linea
            for linea in self.price_list_id.pricelist_line_ids
        }
        for record in self:
            clave = (record.price_list_id.id, record.supply_id.id)
            record.pricelist_line_id = lineas_por_lista_e_insumo.get(clave, False)

            if record.price_list_id and not record.pricelist_line_id and record.supply_type != "auxiliaries":
                net_price = 0

                if record.product_template_id:
                    net_price = record.product_template_id.list_price

                pricelist_line = (
                    self.env["s.budget.pricelist.line"]
                    .with_user(SUPERUSER_ID)
                    .create(
                        {
                            "price_list_id": record.price_list_id.id,
                            "supply_id": record.supply_id.id,
                            "uom_id": record.uom_id.id,
                            "price": net_price,
                        }
                    )
                )
                record.pricelist_line_id = pricelist_line.id
                lineas_por_lista_e_insumo[clave] = pricelist_line

    @api.depends("pricelist_line_id", "pricelist_line_id.quantity", "pricelist_line_id.price", "uom_id")
    def _set_pricelist_price_unit(self):
        for record in self:
            record.price_unit = 0

            for component in record.component_ids:
                record.price_unit += component.price_total

            if record.uom_id and record.pricelist_line_id.uom_id:
                converted_qty = record.uom_id._compute_quantity(
                    record.pricelist_line_id.quantity, record.pricelist_line_id.uom_id
                )
                record.price_unit = converted_qty * record.pricelist_line_id.price
            else:
                record.price_unit = record.product_template_id.list_price

    @api.depends("price_unit", "quantity")
    def _set_price_total(self):
        for rec in self:
            rec.price_total = rec.price_unit * rec.quantity

    @api.onchange("supply_id")
    def _onchange_supply_id(self):
        for record in self:
            record.update(
                {
                    "description": record.supply_id.description or "",
                    "uom_id": record.supply_id.uom_id.id if record.supply_id else False,
                    "supply_code_aux": (
                        record.supply_id.code if record.supply_id else False
                    ),
                }
            )

    def action_open_component_form(self):
        action = {
            "type": "ir.actions.act_window",
            "name": _("Component"),
            "res_model": "s.budget.const.concept.component",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
        return action

    def _copy_children(self, copied_component):
        for child in self.component_ids:
            child_default = {
                "parent_id": copied_component.id,
            }
            copied_child = child.copy(child_default)
            child._set_price_list_line_id()
            child._copy_children(copied_child)

    def action_save_and_stay(self):
        action = {
            "type": "ir.actions.act_window",
            "name": _("Component"),
            "res_model": "s.budget.const.concept.component",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
        return action

    def action_close_and_open_new_wizard(self):
        action = True
        if self.parent_id:
            action = {
                "type": "ir.actions.act_window",
                "name": _("Component"),
                "res_model": "s.budget.const.concept.component",
                "res_id": self.parent_id.id,
                "view_mode": "form",
                "target": "new",
            }
        if self.concept_id:
            action = {
                "type": "ir.actions.act_window",
                "name": _("Concept"),
                "res_model": "s.budget.const.concept",
                "res_id": self.concept_id.id,
                "views": [
                    (
                        self.env.ref(
                            "s_budget_construction.budget_concept_view_form"
                        ).id,
                        "form",
                    )
                ],
                "target": "new",
            }
        return action