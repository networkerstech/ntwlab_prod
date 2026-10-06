# -*- coding: utf-8 -*-
{
    "name": "Budgets Constructions",
    "summary": """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    "description": """
        Long description of module's purpose
    """,
    "author": "SUITEDOO",
    "website": "https://www.suitedoo.com",
    "category": "Uncategorized",
    "version": "19.0.20261005.01",
    "depends": ["base", "web", "uom", "stock", "project", "hr", "hr_hourly_cost", "fleet"],
    "data": [
        "data/data.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        # views
        "views/budget_supply_views.xml",
        "views/product_views.xml",
        "views/budget_concept_views.xml",
        "views/budget_item_views.xml",
        "views/budget_views.xml",
        "views/budget_pricelist_view.xml",
        "views/hr_employee_view.xml",
        "views/fleet_vehicle_view.xml",
        "views/menu.xml",
        "views/budget_gang_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # "s_budget_construction/static/src/services/*",
            "s_budget_construction/static/src/views/**/*",
        ],
    },
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": False,
    'license': 'AGPL-3',
}
