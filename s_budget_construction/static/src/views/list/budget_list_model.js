/** @odoo-module **/

import { listView } from "@web/views/list/list_view";
import { BudgetItemModelMixin, BudgetItemRecordMixin } from "../model_mixin";

const ListModel = listView.Model;

export class BudgetItemModel extends BudgetItemModelMixin(ListModel) {}

BudgetItemModel.Record = class BudgetItemtRecord extends BudgetItemRecordMixin(ListModel.Record) {};