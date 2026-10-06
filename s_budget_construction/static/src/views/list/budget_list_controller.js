/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { _t } from "@web/core/l10n/translation";
import { preSuperSetup, useBudgetItemView } from "@s_budget_construction/views/hooks";
import { useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export class BudgetItemListController extends ListController {
    setup() {
        preSuperSetup();

        super.setup(...arguments);
        this.budgetSharedState = useService("budget_shared_state");
        const properties = useBudgetItemView();
        Object.assign(this, properties);
        this.rootEl = useRef('root');

        const reloadSearchModel = this._reloadSearchModel.bind(this.env.searchModel);
        this.env.bus.addEventListener("BUDGET:ITEM-ADDED", reloadSearchModel);
        this.env.bus.addEventListener("BUDGET:ITEM-REMOVED", reloadSearchModel);
    }

    destroy() {
        this._isDestroyed = true;
        if (super.destroy) {
            super.destroy();
        }
    }

    async _reloadSearchModel() {
        try {
            // Verifica si el componente sigue activo
            if (this._isDestroyed) return;

            const sections = await this.getSections(
                (s) => s.type === "category" && s.fieldName === "parent_id"
            );
            if (this._isDestroyed) return;

            await this._fetchSections(sections, []);
            if (this._isDestroyed) return;

            await this._notify();
        } catch (error) {
            // Si se produce el error por componente destruido, se ignora silenciosamente
            if (error.message === "Component is destroyed") {
                return;
            }
            // Para otros errores, se puede loggear o relanzar
            console.error("Error en _reloadSearchModel:", error);
            throw error;
        }
    }


    get modelParams() {
        const modelParams = super.modelParams;
        modelParams.multiEdit = true;
        return modelParams;
    }

    async onClickCreateGrouper() {
        this.model.root.context.default_item_type = 'grouper';
        return this.onClickCreate();
    }

    async onClickCreateConcept() {
        this.model.root.context.default_item_type = 'concept';
        return this.onClickCreate();
    }

    async onClickCreate() {
        let max_sequence = 0;
        for (let record in this.model.root.records) {
            if (this.model.root.records[record].data.sequence > max_sequence) {
                max_sequence = this.model.root.records[record].data.sequence;
            }
        }
        this.model.root.context.default_sequence = max_sequence + 1;
        this.model.root.context.default_parent_id = this.budgetSharedState.getValue('budget_item_default_parent_id');
        return super.onClickCreate();
    }

    async onRecordSaved(record) {
        let bus = this.env.bus;
        await super.onRecordSaved(...arguments);
//        await this._reloadSearchModel();
        bus.trigger("BUDGET:ITEM-ADDED");
    }

    get deleteConfirmationDialogProps() {
        let props = super.deleteConfirmationDialogProps;
        let _this = this;
        let bus = this.env.bus;
        props.confirm = async function () {
            await _this.model.root.deleteRecords();
        }
        return props;
    }


}

BudgetItemListController.template = "s_budget_construction.BudgetItemListController";
