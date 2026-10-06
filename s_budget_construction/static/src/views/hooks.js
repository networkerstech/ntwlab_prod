/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useSetupAction } from "@web/search/action_hook";
import { useService } from "@web/core/utils/hooks";
import { EventBus, useComponent, useEnv, useRef, useSubEnv } from "@odoo/owl";


/**
 * To be executed before calling super.setup in view controllers.
 */
export function preSuperSetup() {
    // Otherwise not available in model.env
    useSubEnv({
        budgetsView: {
            bus: new EventBus(),
        },
    });

    const component = useComponent();
    const props = component.props;

    // Root state is shared between views to keep the selection
    if (props.globalState && props.globalState.sharedSelection) {
        if (!props.state) {
            props.state = {};
        }
        if (!props.state.modelState) {
            props.state.modelState = {};
        }

        props.state.modelState.sharedSelection = props.globalState.sharedSelection;
    }
}

/**
 * Sets up the env required by budgets view, as well as any other hooks.
 * Returns properties to be applied to the calling component. The code
 * assumes that those properties are assigned to the component.
 */
export function useBudgetItemView() {
    const component = useComponent();
    const props = component.props;
    const root = useRef("root");
    const orm = useService("orm");
    const budgetSharedState = useService("budget_shared_state");

    const notification = useService("notification");
    const dialogService = useService("dialog");
    const action = useService("action");

    // Env setup
    useSubEnv({
        model: component.model,
    });
    const env = useEnv();

    // Keep selection between views
    useSetupAction({
        rootRef: root,
        getGlobalState: () => ({
            sharedSelection: component.model.exportSelection(),
        }),
    });

    return {
        budgetSharedState,
        // Refs
        root,
        // Services
        orm,
        notification,
        dialogService,
        actionService: action,
        // Helpers
        hasShareItems: () => {
            const budgetItem = env.searchModel.getSelectedParent();
            const selectedRecords = env.model.root.selection.length;
            return !budgetItem.id && !selectedRecords;
        },
    };
}

