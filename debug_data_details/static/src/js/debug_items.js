/** @odoo-module **/

import { deepCopy } from "@web/core/utils/objects";
import { Dialog } from "@web/core/dialog/dialog";
import { generateLegacyLoadViewsResult } from "@web/legacy/legacy_load_views";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { viewService } from "@web/views/view_service";

const debugRegistry = registry.category("debug");

patch(Dialog.prototype, "web_debug_Dialog", {
    get isFormAllData() {
        if(this.props && this.props.actionProps && this.props.actionProps.context 
                && this.props.actionProps.context.open_all_data) {
            return false;
        }
        return true;
    }
})

patch(viewService, "debug_data_details_viewService", {
    start(env, { orm }) {
        let cache = {};

        env.bus.addEventListener("CLEAR-CACHES", () => {
            cache = {};
            const processedArchs = registry.category("__processed_archs__");
            processedArchs.content = {};
            processedArchs.trigger("UPDATE");
        });

        /**
         * Loads fields information
         *
         * @param {string} resModel
         * @param {LoadFieldsOptions} [options]
         * @returns {Promise<object>}
         */
        async function loadFields(resModel, options = {}) {
            const key = JSON.stringify([
                "fields",
                resModel,
                options.fieldNames,
                options.attributes,
            ]);
            if (!cache[key]) {
                cache[key] = orm
                    .call(resModel, "fields_get", [options.fieldNames, options.attributes])
                    .catch((error) => {
                        delete cache[key];
                        return Promise.reject(error);
                    });
            }
            return cache[key];
        }

        /**
         * Loads various information concerning views: fields_view for each view,
         * fields of the corresponding model, and optionally the filters.
         *
         * @param {LoadViewsParams} params
         * @param {LoadViewsOptions} [options={}]
         * @returns {Promise<ViewDescriptions>}
         */
        async function loadViews(params, options = {}) {
            const { context, resModel, views } = params;
            var flag = false
            if(context && context['open_all_data']) {
                flag = true
            }
            const loadViewsOptions = {
                action_id: options.actionId || false,
                load_filters: options.loadIrFilters || false,
                open_all_data: flag,
                toolbar: options.loadActionMenus || true
            };
            if (env.isSmall) {
                loadViewsOptions.mobile = true;
            }
          //  params['views'] = [[false, 'form']]
           // const { context, resModel, views } = params;
            const filteredContext = Object.fromEntries(
                Object.entries(context || {}).filter((k, v) => !String(k).startsWith("default_"))
            );
            const key = JSON.stringify([resModel, views, filteredContext, loadViewsOptions]);
            
            if (flag || !cache[key]) {
                cache[key] = orm
                    .call(resModel,'get_views', [], { context, views, options: loadViewsOptions })
                    .then(async (result) => {
                        const { models, views } = result;
                        const modelsCopy = deepCopy(models); // for legacy views
                        const viewDescriptions = {
                            __legacy__: generateLegacyLoadViewsResult(resModel, views, modelsCopy),
                            fields: models[resModel],
                            relatedModels: models,
                            views: {},
                        };
                        for (const [resModel, fields] of Object.entries(modelsCopy)) {
                            const key = JSON.stringify(["fields", resModel, undefined, undefined]);
                            cache[key] = Promise.resolve(fields);
                        }
                        for (const viewType in views) {
                            const { arch, toolbar, id, filters, custom_view_id } = views[viewType];
                            const viewDescription = { arch, id, custom_view_id };
                            if (toolbar) {
                                viewDescription.actionMenus = toolbar;
                            }
                            if (filters) {
                                viewDescription.irFilters = filters;
                            }
                            viewDescriptions.views[viewType] = viewDescription;
                        }
                        return viewDescriptions;
                    })
                    .catch((error) => {
                        delete cache[key];
                        return Promise.reject(error);
                    });
            }
            return cache[key];
        }
        return { loadViews, loadFields };
    },
});

function openFormAllData({ component, env }) {
    const resId = component.model.root.resId;
    const resModel = component.model.root.resModel;
    if (!resId) {
        return null; // No record
    }
    const description = env._t("View all data");
    return {
        type: "item",
        description,
        callback: () => {
            env.services.action.doAction({
                res_model: resModel,
                res_id: resId,
                name: description,
                views: [
                    [false, "form"],
                ],
                type: "ir.actions.act_window",
                context: {
                    'open_all_data': 'open_all_data',
                    'create': false,
                    'edit': false,
                },
                target: 'new',
            });
        },
        sequence: 110,
    };
}
debugRegistry.category("form").add("openFormAllData", openFormAllData);
