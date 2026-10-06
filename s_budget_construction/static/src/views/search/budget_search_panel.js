/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";


/**
 * This file defines the BudgetItemSearchPanel component, an extension of the
 * SearchPanel to be used in the documents kanban/list views.
 */

export class BudgetItemSearchPanel extends SearchPanel {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.user = user;
        this.action = useService("action");
        this.dialog = useService("dialog");
    }

    async _reloadSearchModel() {
        // By default the category is not reloaded.
        const searchModel = this.env.searchModel;
        await searchModel._fetchSections(
            searchModel.getSections(
                (s) => s.type === "category" && s.fieldName === "parent_id"
            ),
            []
        );

        await searchModel._notify();
    }


}

BudgetItemSearchPanel.modelExtension = "BudgetItemSearchPanel";

// web.SearchPanel.Small (mobile) renders web.SearchPanel.Section directly and
// resolves constructor.subTemplates dynamically, so the same templates and
// subTemplates apply to both desktop and mobile since Odoo 19.
BudgetItemSearchPanel.template = "s_budget_construction.SearchPanel";
BudgetItemSearchPanel.subTemplates = {
    category: "s_budget_construction.SearchPanel.Category",
    filtersGroup: "s_budget_construction.SearchPanel.FiltersGroup",
};
