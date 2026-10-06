/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ListRenderer } from "@web/views/list/list_renderer";

import { useRef } from "@odoo/owl";

export class BudgetItemListRenderer extends ListRenderer {
    static props = [...ListRenderer.props];
    static template = "s_budget_construction.BudgetItemListRenderer";
    static recordRowTemplate = "s_budget_construction.BudgetItemListRenderer.RecordRow";

    static components = Object.assign({}, ListRenderer.components, {});

    setup() {
        super.setup();
        this.root = useRef("root");
    }
}
