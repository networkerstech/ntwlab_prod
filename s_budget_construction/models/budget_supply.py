# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.orm.identifiers import NewId

from .supply_type import SUPPLY_TYPES


class BudgetConstructionSypply(models.Model):
    _name = "s.budget.const.supply.type"
    _description = "Supply Type"
    _rec_name = "display_name"

    code = fields.Char("Code")
    code_suply = fields.Char("Code", compute="_set_display_name")
    name = fields.Char("Name", translate=True)
    display_name = fields.Char("Full name", compute="_set_display_name", compute_sudo=False)
    supply_type = fields.Selection(
        [item for item in SUPPLY_TYPES.items()],
        string="Type",
        compute="_set_supply_type",
        store=True,
        readonly=False,
        recursive=True,
    )

    parent_id = fields.Many2one("s.budget.const.supply.type", "Parent")

    parent_code = fields.Char(
        "Parent Code",
        store=True,
    )
    child_ids = fields.One2many("s.budget.const.supply.type", "parent_id", "Children")

    @api.depends("parent_id", "code", "name")
    def _set_display_name(self):
        for rec in self:
            item = rec
            item_path = []
            item_path_cd = []
            while item:
                item_path_cd.append("%s" % (item.code))
                item_path.append("[%s] - %s" % (item.code, item.name))
                item = item.parent_id
            item_path.reverse()
            rec.code_suply = "/".join(item_path_cd)
            rec.display_name = "/".join(item_path)

    @api.depends("parent_id", "parent_id.supply_type")
    def _set_supply_type(self):
        for rec in self:
            if rec.parent_id:
                rec.supply_type = rec.parent_id.supply_type

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if val.get("parent_code", False):
                types_obj = self.search(
                    [
                        ("code", "=", val.get("parent_code", False)),
                        ("parent_id", "=", False),
                    ],
                    limit=1,
                )
                if types_obj:
                    types_obj = types_obj[0]
                    val.update({"parent_id": types_obj.id})

        res = super().create(vals)
        return res


class BudgetConstructionSypply(models.Model):
    _name = "s.budget.const.supply"
    _description = "Construction Budget Supply"
    _rec_name = "display_name"

    code = fields.Char("Code")
    code_suply = fields.Char("Code", compute="_set_display_name", store=True)
    display_name = fields.Char("Full name", compute="_set_display_name", compute_sudo=False, store=True)
    product_template_id = fields.Many2one(
        comodel_name="product.template", string="Product"
    )
    fleet_vehicle_id = fields.Many2one(comodel_name="fleet.vehicle", string="Vehicle")
    budget_gang_id = fields.Many2one(comodel_name="budget.gang", string="Gang")

    @api.depends("supply_type_id", "code", "description")
    def _set_display_name(self):
        for rec in self:
            rec.code_suply = "/".join(
                [str(rec.supply_type_id.code_suply)] + [str(rec.code)]
            )
            rec.display_name = "/".join(
                [str(rec.supply_type_id.code_suply)]
                + [str(rec.code) + "-" + str(rec.description)]
            )

    description = fields.Char("Description")
    supply_type_id = fields.Many2one(
        "s.budget.const.supply.type",
        "Supply type",
        domain="[('parent_id', '!=', False)]",
    )
    supply_type = fields.Selection(
        related="supply_type_id.supply_type", readonly=True, store=True
    )
    uom_id = fields.Many2one("uom.uom", string="Unit")
    currency_id = fields.Many2one(
        string="Currency",
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    price_unit = fields.Float("Price unit")

    component_ids = fields.One2many(
        "s.budget.const.concept.suply.component", "parent_id", "Componets"
    )

    component_material_ids = fields.One2many(
        "s.budget.const.concept.suply.component",
        "parent_id",
        "Componets",
        copy=False,
        domain=[("supply_type", "=", "material")],
    )
    component_work_force_ids = fields.One2many(
        "s.budget.const.concept.suply.component",
        "parent_id",
        "Work force componets",
        domain=[("supply_type", "=", "work_force")],
        copy=False,
    )
    component_tools_ids = fields.One2many(
        "s.budget.const.concept.suply.component",
        "parent_id",
        "Tools componets",
        domain=[("supply_type", "=", "tools")],
        copy=False,
    )
    component_machinery_ids = fields.One2many(
        "s.budget.const.concept.suply.component",
        "parent_id",
        "Machinery componets",
        domain=[("supply_type", "=", "machinery")],
        copy=False,
    )
    component_transport_cost_ids = fields.One2many(
        "s.budget.const.concept.suply.component",
        "parent_id",
        "Transport cost componets",
        domain=[("supply_type", "=", "transport_cost")],
        copy=False,
    )


class ConceptSuplyBudget(models.Model):
    _name = "s.budget.const.concept.suply.component"

    proj_id = fields.Char("Proj")
    concept_code = fields.Char("Concepto")
    parent_code = fields.Char("Parent")
    product_template_id = fields.Many2one(
        comodel_name="product.template", string="Product"
    )
    fleet_vehicle_id = fields.Many2one(comodel_name="fleet.vehicle", string="Vehicle")
    budget_gang_id = fields.Many2one(comodel_name="budget.gang", string="Gang")

    supply_code_aux = fields.Char(
        "Code",
    )
    supply_code = fields.Char(
        "Code",
        related="supply_id.code",
        readonly=False,
        store=True,
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

    supply_id = fields.Many2one("s.budget.const.supply", string="Supply")
    supply_type = fields.Selection(
        [item for item in SUPPLY_TYPES.items()], default=_get_default_supply_type
    )
    description = fields.Char("Description")
    uom_id = fields.Many2one("uom.uom", "UM")
    quantity = fields.Float("Quantity", digits=(16, 7))
    price_total = fields.Float("Price total", compute="_set_price_total")

    parent_id = fields.Many2one("s.budget.const.supply", string="Parent")

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
