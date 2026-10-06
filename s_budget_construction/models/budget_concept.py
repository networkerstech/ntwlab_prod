# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID, Command
from odoo.orm.identifiers import NewId

from .supply_type import SUPPLY_TYPES


class BudgetConcept(models.Model):
    _name = "s.budget.const.concept"
    _description = "Concept"
    _rec_name = "code"

    _sql_constraints = [
        (
            "budget_code_unique_by_project",
            "unique (code, project_id)",
            "Concept code must be unique by budget.",
        ),
    ]

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
        for concept in self:
            component_ids = concept.component_ids | concept.component_ids.mapped('component_ids')
            for component in component_ids:
                if not component.supply_id:
                    supply = self.env["s.budget.const.supply"].search(
                            [
                                ("code", "=", component.supply_code_aux),
                            ],
                            limit=1,
                        )
                    if not supply:
                        supply_type_id = self.env["s.budget.const.supply.type"].search(
                            [("supply_type", "=", component.supply_type)], limit=1
                        )
                        new_supply = self.env["s.budget.const.supply"].create(
                            {
                                "code": component.supply_code_aux,
                                "description": component.description,
                                "uom_id": component.uom_id.id,
                                "price_unit": component.price_unit,
                                "supply_type_id": supply_type_id.id,
                                "product_template_id": component.product_template_id.id,
                                "budget_gang_id": component.budget_gang_id.id,
                                "fleet_vehicle_id": component.fleet_vehicle_id.id,
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
                    ca.component_ids = [(5, 0, 0)]
                    component_vals = []
                    for supply_component in ca.supply_id.component_ids:
                        component_vals.append(
                            (
                                0,
                                0,
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
                                },
                            )
                        )
                    ca.component_ids = component_vals


class BudgetConceptComponent(models.Model):
    _name = "s.budget.const.concept.component"
    _description = "Construction budget componet line"

    proj_id = fields.Char("Proj")
    concept_code = fields.Char("Concepto")
    parent_code = fields.Char("Parent")
    concept_id = fields.Many2one("s.budget.const.concept", string="Concept")
    product_template_id = fields.Many2one(
        comodel_name="product.template", string="Product"
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
        "Code",
    )
    supply_code = fields.Char(
        "Code",
        related="supply_id.code",
        readonly=False,
        store=True,
    )

    @api.onchange("supply_code_aux")
    def _onchange_supply_code(self):
        if self.supply_code_aux and isinstance(self.id, NewId):
            supply = self.env["s.budget.const.supply"].search(
                [
                    ("code", "=", self.supply_code_aux),
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
            # self.supply_code_aux = self.product_template_id.default_code
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

    # @api.onchange("supply_code_aux")
    # def _onchange_supply_code_aux(self):
    #     if self.supply_code_aux:
    #         if self.env.context.get('is_all', False):
    #             product_id = self.env["product.template"].search(
    #                 [
    #                     ("default_code", "=", self.supply_code_aux),
    #                     ("build_ok", "=", True),
    #                 ], limit=1
    #             )
    #             if product_id:
    #                 self.product_template_id = product_id
    #                 self.description = product_id.name
    #                 self.uom_id = product_id.uom_id
    #         elif self.env.context.get('is_material', False):
    #             product_id = self.env["product.template"].search(
    #                 [
    #                     ("default_code", "=", self.supply_code_aux),
    #                     ("supply_type", "=", 'material'),
    #                     ("build_ok", "=", True),
    #                 ], limit=1
    #             )
    #             if product_id:
    #                 self.product_template_id = product_id
    #                 self.description = product_id.name
    #                 self.uom_id = product_id.uom_id
    #         elif self.env.context.get('is_work_force', False):
    #             budget_gang_id = self.env["budget.gang"].search(
    #                 [
    #                     ("build_ok", "=", True),
    #                     ("internal_reference", "=", self.supply_code_aux),
    #                     ("supply_type", "=", 'work_force'),
    #                 ], limit=1
    #             )
    #             if budget_gang_id:
    #                 self.budget_gang_id = budget_gang_id
    #                 self.description = budget_gang_id.name
    #         elif self.env.context.get('is_tools', False):
    #             product_id = self.env["product.template"].search(
    #                 [
    #                     ("build_ok", "=", True),
    #                     ("tool_ok", "=", True),
    #                     ("default_code", "=", self.supply_code_aux),
    #                     ("supply_type", "=", 'tools'),
    #                 ], limit=1
    #             )
    #             if product_id:
    #                 self.product_template_id = product_id
    #                 self.description = product_id.name
    #                 self.uom_id = product_id.uom_id
    #         elif self.env.context.get('is_machinery', False):
    #             product_id = self.env["product.template"].search(
    #                 [
    #                     ("build_ok", "=", True),
    #                     ("machinery_ok", "=", True),
    #                     ("default_code", "=", self.supply_code_aux),
    #                     ("supply_type", "=", 'machinery'),
    #                 ], limit=1
    #             )
    #             if product_id:
    #                 self.product_template_id = product_id
    #                 self.description = product_id.name
    #                 self.uom_id = product_id.uom_id

    # @api.onchange('product_template_id', 'fleet_vehicle_id', 'budget_gang_id')
    # def _onchange_supply_type(self):
    #     for rec in self:
    #         if rec.product_template_id:
    #             rec.supply_code_aux = rec.product_template_id.default_code
    #             rec.supply_type = rec.product_template_id.supply_type
    #         elif rec.fleet_vehicle_id:
    #             rec.supply_type = rec.fleet_vehicle_id.supply_type
    #         elif rec.budget_gang_id:
    #             rec.supply_type = rec.budget_gang_id.supply_type
    #         else:
    #             rec.supply_type = rec.supply_type

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

    supply_id = fields.Many2one("s.budget.const.supply", string="Supply", store=True)
    
    supply_type = fields.Selection(
        [item for item in SUPPLY_TYPES.items()], default=_get_default_supply_type
    )
    # supply_type = fields.Selection(
    #     [item for item in SUPPLY_TYPES.items()]
    # )
    description = fields.Char("Description")
    price_unit = fields.Float("Price unit", compute="_set_pricelist_price_unit")
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

    @api.depends("concept_price_list_id", "parent_id")
    def _set_pricelist_id(self):
        for rec in self:
            if rec.concept_price_list_id:
                rec.price_list_id = rec.concept_price_list_id.id
            if rec.parent_id:
                rec.parent_id._set_pricelist_id()
                rec.price_list_id = rec.parent_id.price_list_id.id

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
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
        res = super().create(vals)
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

    @api.depends("price_list_id", "supply_id")
    def _set_price_list_line_id(self):
        for rec in self:
            rec.pricelist_line_id = False
            for r in rec.price_list_id.pricelist_line_ids:
                if r.supply_id.id == rec.supply_id.id:
                    rec.pricelist_line_id = r.id
            if (
                rec.price_list_id
                and not rec.pricelist_line_id
                and rec.supply_type != "auxiliaries"
            ):
                pricelist_line = (
                    self.env["s.budget.pricelist.line"]
                    .with_user(SUPERUSER_ID)
                    .create(
                        {
                            "price_list_id": rec.price_list_id.id,
                            "supply_id": rec.supply_id.id,
                            "uom_id": rec.uom_id.id,
                            "price": 0.0,
                        }
                    )
                )
                rec.pricelist_line_id = pricelist_line.id

    @api.depends(
        "pricelist_line_id",
        "pricelist_line_id.quantity",
        "pricelist_line_id.price",
        "uom_id",
    )
    def _set_pricelist_price_unit(self):
        for rec in self:
            rec.price_unit = 0
            for r in rec.component_ids:
                rec.price_unit += r.price_total
            if rec.uom_id and rec.pricelist_line_id.uom_id:
                converted_qty = rec.uom_id._compute_quantity(
                    rec.pricelist_line_id.quantity, rec.pricelist_line_id.uom_id
                )
                rec.price_unit = converted_qty * rec.pricelist_line_id.price

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
