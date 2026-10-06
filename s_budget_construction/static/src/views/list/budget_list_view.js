/** @odoo-module **/

import { registry } from "@web/core/registry";


import { listView } from "@web/views/list/list_view";
import { BudgetItemListController } from "./budget_list_controller";
import { BudgetItemModel } from "./budget_list_model";
import { BudgetItemListRenderer } from "./budget_list_renderer";
import { BudgetItemSearchModel as BudgetItemSearchModel } from "../search/budget_search_model";
import { BudgetItemSearchPanel as BudgetItemSearchPanel } from "../search/budget_search_panel";

export const BudgetItemListView = Object.assign({}, listView, {
    SearchModel: BudgetItemSearchModel,
    SearchPanel: BudgetItemSearchPanel,
    Controller: BudgetItemListController,
    Model: BudgetItemModel,
    Renderer: BudgetItemListRenderer,
    searchMenuTypes: [],
});

registry.category("views").add("budget_item_list", BudgetItemListView);
