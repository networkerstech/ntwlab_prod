# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.orm.identifiers import NewId
from odoo.fields import Domain
import ast


class BudgetConstructionItem(models.Model):
    _inherit = "project.task"

    item_type = fields.Selection(
        [("grouper", "Grouper"), ("concept", "Concept")], "Item type", default="grouper"
    )
    concept_id = fields.Many2one(
        "s.budget.const.concept", "Concept", help="Like inherits"
    )
                
    concept_template_id = fields.Many2one(
        related='concept_id.concept_template_id')

    is_a_buget_template = fields.Boolean(
        related='project_id.is_a_buget_template', store=True)
    # Concept related
    grouper_code = fields.Char(
        "Código del Agrupador",
    )
    budget_code = fields.Char(
        "Code",
        # compute="_set_concept_related",
    )
    parent_code = fields.Char(
        "Parent Code",
    )
    template_code_aux = fields.Char(
        "Template Code",
        readonly=False,
        store=True,
    )
    template_code = fields.Char(
        "Template Code",
        related="concept_template_id.code",
        readonly=False,
        store=False,
    )
    
    componens = fields.Char(string='Datos', store=True)
    
    budget_description = fields.Text(
        "Description",
        related="concept_id.description",
        # compute="_set_concept_related",
        readonly=False,
        store=False,
    )
    budget_uom_id = fields.Many2one(
        "uom.uom",
        related="concept_id.uom_id",
        # compute="_set_concept_related",
        string="Uom",
        readonly=False,
        store=False,
    )
    budget_price_unit = fields.Float(
        "Price Unit",
        readonly=False,
        store=False,
        compute="_set_child_ids_price_total",
        recursive=True,
    )

    # item fields
    budget_qty = fields.Float("Quantity")
    budget_price_total = fields.Float(
        "Price total", compute="_set_budget_price_total")

    @api.depends("budget_price_unit", "budget_qty")
    def _set_price_total(self):
        for rec in self:
            rec.budget_price_total = rec.budget_price_unit * rec.budget_qty

    @api.depends(
        "child_ids",
        "child_ids.budget_price_unit",
        "child_ids.budget_price_total",
        "concept_id",
        "concept_id.price_unit",
    )
    def _set_child_ids_price_total(self):
        for rec in self:
            rec.budget_price_unit = 0
            if rec.concept_id:
                rec.budget_price_unit = rec.concept_id.price_unit
            for ch in rec.child_ids:
                rec.budget_price_unit += ch.budget_price_total

    @api.model_create_multi
    def create(self, vals):
        res = self
        for val in vals:
            # sync project_task
            val.update(
                {
                    "description": val.get("budget_description", ""),
                }
            )
            if (
                val.get("parent_code", False)
            ):
                parent = res.search(
                    [   '|',
                            ("budget_code", "=", val.get("parent_code", False)),
                            ("grouper_code", "=", val.get("parent_code", False)),
                            ("project_id", "=", val.get("project_id", False)),
                        ], limit=1
                    )
                if parent:
                    parent = parent[0]
                    val.update({"parent_id": parent.id})
            if (
                not val.get("concept_id", False)
                and val.get("item_type", "") == "concept"
            ):
                if val.get("budget_code", False) and not val.get("is_a_buget_template", False):
                    concept = self.env["s.budget.const.concept"].search(
                        [
                            ("code", "=", val.get("budget_code", False)),
                            ("project_id", "=", val.get("project_id", False)),
                        ], limit=1
                    )
                    if concept:
                        concept = concept[0]
                        val.update({"concept_id": concept.id})
                if not val.get("concept_id", False):
                    concept = self.env["s.budget.const.concept"].create(
                        {
                            "code": val.get("budget_code", ""),
                            "name": val.get("name", ""),
                            "description": val.get("budget_description") or val.get("name", ""),
                            "uom_id": val.get("budget_uom_id", ""),
                            "price_unit": val.get("budget_price_unit", ""),
                            "project_id": val.get("project_id", False),
                        }
                    )
                    val.update({"concept_id": concept.id})
            if not val.get("budget_description"):
                val.pop("budget_description", None)
            res = res | super().create(val)
        for r in res:
            if r.template_code_aux:
                r.template_code = r.template_code_aux
                r._onchange_template_code_aux()
        return res

    def write(self, vals):
        for field in vals:
            # sync project_task
            if field == "budget_description":
                vals.update(
                    {
                        "description": vals.get("budget_description", ""),
                    }
                )
        if "name" in vals and not self.env.context.get("change_in_concept", False):
            for record in self:
                record.concept_id.write({'name': vals.get('name')})
        return super().write(vals)

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        if self.env.context.get("use_budget_item_view", False):
            act_model = self.env.context.get("active_model", False)
            act_id = self.env.context.get("active_id", False)

            if act_model == "project.project" and act_id:
                res.update({"project_id": act_id})

        return res

    @api.depends(
        "concept_id",
        "concept_id.code",
        "concept_id.description",
        "concept_id.uom_id",
        "concept_id.price_unit",
    )
    def _set_concept_related(self):
        for rec in self:
            if rec.concept_id:
                # rec.budget_code = rec.concept_id.code
                rec.budget_description = rec.concept_id.description
                rec.budget_uom_id = rec.concept_id.uom_id
                rec.budget_price_unit = rec.concept_id.price_unit

    @api.depends("budget_qty", "budget_price_unit")
    def _set_budget_price_total(self):
        for rec in self:
            rec.budget_price_total = rec.budget_price_unit * rec.budget_qty

    @api.onchange("budget_description")
    def _onchange_budget_description(self):
        """
        Para evitar dict size change al editar
        """
        self.description = self.budget_description

    def _onchange_template_code_aux(self):
        if self.template_code and not self.concept_id.concept_template_id and not self.is_a_buget_template:
            concept_tmpl = self.env["s.budget.const.concept"].search(
                    [
                        ("code", "=", self.template_code),
                        ("is_a_buget_template", "=", True)
                    ], limit=1
                )
            if concept_tmpl:
                default = {
                        'project_id': self.project_id.id,
                        'price_list_id': self.concept_id.price_list_id.id
                    }
                if not self.concept_id:
                    concept = concept_tmpl[0].copy(default)
                    self.concept_id = concept
                    # self.budget_code = concept.code
                    self.name = concept.name
                    self.budget_description = concept.description
                    self.budget_uom_id = concept.uom_id
                    self.concept_id.concept_template_id = concept_tmpl[0].id
                else:
                    if not self.concept_id.concept_template_id:
                        concept = concept_tmpl[0]._copy_children(self.concept_id)
                        self.concept_id.concept_template_id = concept_tmpl[0].id
                        
    @api.onchange("template_code")
    def _onchange_template_code(self):
        if self.template_code and isinstance(self.id, NewId) and not self.is_a_buget_template:
            task = self.env['project.task'].search(
                [
                    ('item_type', '=', 'concept'),
                    ('budget_code', '=', self.template_code),
                    ('is_a_buget_template', '=', True),
                ], limit=1
            )
            concept_tmpl = task.concept_id
            # concept_tmpl = self.env["s.budget.const.concept"].search(
            #         [
            #             ("code", "=", self.template_code),
            #             ("is_a_buget_template", "=", True)
            #         ], limit=1
            #     )
            if concept_tmpl:
                default = {
                        'project_id': self.project_id.id,
                        'price_list_id': self.concept_id.price_list_id.id
                    }
                if not self.concept_id:
                    concept = concept_tmpl[0].copy(default)
                    self.concept_id = concept
                    # self.budget_code = concept.code
                    self.name = concept.name
                    self.budget_description = concept.description
                    self.budget_uom_id = concept.uom_id
                    self.concept_id.concept_template_id = concept_tmpl[0].id
                else:
                    if not self.concept_id.concept_template_id:
                        concept = concept_tmpl[0]._copy_children(self.concept_id)
                        self.concept_id.concept_template_id = concept_tmpl[0].id

    @api.onchange("budget_code")
    def _onchange_budget_code(self):
        if self.item_type == "concept" and self.budget_code and isinstance(self.id, NewId) and not self.is_a_buget_template:
            "Si en el momento de crear un elemento ya existe se asocia a este"
            concept = self.env["s.budget.const.concept"].search(
                [
                    ("code", "=", self.budget_code),
                    ("project_id", "=", self.project_id.id),
                ], limit=1
            )
            if concept:
                default = {
                        'project_id': self.project_id.id,
                        'price_list_id': self.concept_id.price_list_id.id
                    }
                if not self.concept_id:
                    concept = concept[0]
                    self.concept_id = concept
                    # self.budget_code = concept.code
                    self.name = concept.name
                    self.budget_description = concept.description
                    self.budget_uom_id = concept.uom_id
           

    @api.model
    def web_search_read(
        self, domain, specification, offset=0, limit=None, order=None, count_limit=None
    ):
        """Cuando en el contexto está presente la clave 'use_budget_item_view'
        indicando que es la vista de items del presupuesto:
        * Mostrar solo los items de primer del presupuesto activo
        * Si no está seleccionado ningún item muestran los agrupadores 'raíz'
        [("parent_id", "=", False)]
        * Si está seleccionado un item se muestran los hijos directos de este, en lugar de
        'child_of' se usa '=', [("parent_id", "=", parent_id)]
        """
        new_context = dict(self.env.context or {})
        if self._name == "project.task" and new_context.get(
            "use_budget_item_view", False
        ):
            # Asegurar que el dominio sea una lista
            if not domain or not isinstance(domain, (tuple, list)):
                domain = []
            act_id = new_context.get("active_id", False)

            has_child_of_parent_id = any(
                isinstance(leaf, (tuple, list))
                and leaf[0] == "parent_id"
                and leaf[1] == "child_of"
                for leaf in domain
            )
            if not domain or not has_child_of_parent_id:
                domain = Domain.AND([domain, [("parent_id", "=", False)]])
            else:
                for leaf in domain:
                    if (
                        isinstance(leaf, (tuple, list))
                        and leaf[0] == "parent_id"
                        and leaf[1] == "child_of"
                    ):
                        leaf[1] = "="

            # mostrar solo los elementos del presupuesto
            if act_id:
                domain = Domain.AND([domain, [("project_id", "=", act_id)]])
                new_context.update({"default_project_id": act_id})

        return super(
            BudgetConstructionItem, self.with_context(new_context)
        ).web_search_read(domain, specification, offset, limit, order, count_limit)

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        if self._name == "project.task" and (self.env.context.get( "use_budget_item_view", False)
                                             or self.env.context.get( "use_budget_template_item_view", False)):
            act_model = self.env.context.get("active_model")
            act_id = self.env.context.get("active_id", False)
            pjct = self.env['project.project'].browse(act_id)
            comodel_domain = kwargs.get("comodel_domain", [])
            if act_model == "project.project" and act_id:
                items = self.env["project.task"].search(
                    [("project_id", "=", act_id), ("parent_id", "=", False)]
                )
                if items:
                    comodel_domain = Domain.AND(
                        [comodel_domain, [("id", "child_of", items.ids)]]
                    )
                else:
                    comodel_domain = Domain.AND(
                        [comodel_domain, [("project_id", "=", act_id)]]
                    )
            if not self.env.context.get("default_is_budget_construction", False) and not act_id:
                items = self.env["project.task"].search(
                    [("is_a_buget_template", "=", True), ("parent_id", "=", False)]
                )
                if items:
                    comodel_domain = Domain.AND(
                        [comodel_domain, [("id", "in", items.ids)]]
                    )
                else:
                    comodel_domain = Domain.AND(
                        [comodel_domain, [("id", "=", False)]]
                    )

            kwargs["comodel_domain"] = comodel_domain
        return super().search_panel_select_range(field_name, **kwargs)

    def action_open_concept_form(self):
        action = {
            "type": "ir.actions.act_window",
            "name": _("Concept"),
            "res_model": "s.budget.const.concept",
            "res_id": self.concept_id.id,
            "views": [
                (
                    self.env.ref(
                        "s_budget_construction.budget_concept_view_form").id,
                    "form",
                )
            ],
            "target": "new",
        }
        return action
