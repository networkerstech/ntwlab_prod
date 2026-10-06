/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

export const BudgetItemModelMixin = (component) =>
    class extends component {

        setup(params) {
            super.setup(...arguments);
            if (this.config.resModel === "project.task") {
                this.originalSelection = params.state?.sharedSelection;
            }
        }

        exportSelection() {
            return this.root.selection.map((rec) => rec.resId);
        }

        async load() {
            const selection = this.root?.selection;
            if (selection && selection.length > 0) {
                this.originalSelection = selection.map((rec) => rec.resId);
            }
            const res = await super.load(...arguments);
            if (this.config.resModel !== "project.task") {
                return res;
            }
            this._reapplySelection();
            return res;
        }

        _reapplySelection() {
            const records = this.root.records;
            if (this.originalSelection && this.originalSelection.length > 0 && records) {
                const originalSelection = new Set(this.originalSelection);
                records.forEach((record) => {
                    record.selected = originalSelection.has(record.resId);
                });
                delete this.originalSelection;
            }
        }

    };

export const BudgetItemRecordMixin = (component) => class extends component {

    async update() {
        const originalParentId = this.data.parent_id[0];
        await super.update(...arguments);
        if (this.data.parent_id[0] !== originalParentId) {
            this.model.root._removeRecords(this.model.root.selection.map((rec) => rec.id));
        }
    }
};
