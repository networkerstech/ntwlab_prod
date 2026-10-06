/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { SearchModel } from "@web/search/search_model";
import { browser } from "@web/core/browser/browser";
import { parseHash, router } from "@web/core/browser/router";
import { useSetupAction } from "@web/search/action_hook";
import { useService } from "@web/core/utils/hooks";


export class BudgetItemSearchModel extends SearchModel {

    setup(services) {
        super.setup(services);
        this.budgetSharedState = useService("budget_shared_state");
        useSetupAction({
            beforeLeave: () => {
                this._updateRouteState({ parent_id: undefined }, false);
            },
        });
    }

    async load(config) {
        await super.load(...arguments);

        const urlHash = parseHash(browser.location.hash);
        const parentId = urlHash.parent_id || this.getSelectedParentId();

        if (parentId) {
            const parentSection = this.getSections()[0];
            if (parentSection) {
                this.toggleCategoryValue(parentSection.id, parentId);
            }
        }
    }

    //---------------------------------------------------------------------
    // Actions / Getters
    //---------------------------------------------------------------------

    /**
     * Returns the id of the current selected budged item id, if any, false
     * otherwise.
     * @returns {number | false}
     */
    getSelectedParentId() {
        const { activeValueId } = this.getSections()[0];
        return activeValueId;
    }

    /**
     * Returns the current selected budged item, if any, false otherwise.
     * @returns {Object | false}
     */
    getSelectedParent() {
        const parentSection = this.getSections()[0];
        const parent = parentSection && parentSection.values.get(parentSection.activeValueId);
        return parent || false;
    }


    /**
     * Overridden to write the new value in the local storage.
     * And to write the parent_id in the url.
     * @override
     */
    toggleCategoryValue(sectionId, valueId) {
        const { fieldName } = this.sections.get(sectionId);
        const storageKey = this._getStorageKey(fieldName);
        browser.localStorage.setItem(storageKey, valueId);

        if (fieldName === "parent_id") {
            this._updateRouteState({ parent_id: valueId }, true);
            this.budgetSharedState.setValue('budget_item_default_parent_id', valueId);
        }
        super.toggleCategoryValue(...arguments);
    }



    //---------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------

    /**
     * @private
     * @param {string} fieldName
     * @returns {string}
     */
    _getStorageKey(fieldName) {
        return `searchpanel_${this.resModel}_${fieldName}`;
    }

    /**
     * @override
     */
    _shouldWaitForData() {
        return true;
    }

    _updateRouteState(state, lock = true) {
        router.pushState(state, lock ? { lock: state } : {});
    }

}
