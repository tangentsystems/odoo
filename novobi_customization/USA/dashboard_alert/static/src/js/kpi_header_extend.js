odoo.define('dashboard_alert.alert', function (require) {
    "use strict";

    /**
     * This file defines the US Accounting Dashboard view (alongside its renderer, model
     * and controller), extending the Kanban view.
     * The US Accounting Dashboard view is registered to the view registry.
     * A large part of this code should be extracted in an AbstractDashboard
     * widget in web, to avoid code duplication (see SalesTeamDashboard).
     */

    var HeaderKPIsRenderer = require('account_dashboard.kpi_header')['Renderer'];
    var dialogs = require('dashboard_alert.AlertInfoTreeViewDialog');
    var core = require('web.core');

    var _t = core._t;

    HeaderKPIsRenderer.include({
        events:  _.extend({}, HeaderKPIsRenderer.prototype.events, {
            'click .alert-bell': 'click_alert_bell_btn',
        }),
        //--------------------------------------------------------------------------
        // EVENTS
        //--------------------------------------------------------------------------
        click_alert_bell_btn: function (event) {
            this._searchCreatePopup('search', false, event)
        },
        _searchCreatePopup: function (view, ids, event, context) {
            var self = this;
            var elem = $(event.currentTarget);
            var name_elem = $(elem[0].offsetParent).find('.kpi_name')[0].innerText;
            var index_elem = $.map(this.$el.find('.kpi_name'),
                function(e) {
                    return e.innerText
                }).findIndex(fruit => fruit === name_elem);
            var kpi_id = parseInt(this.$el.find('.kpi_id')[index_elem].innerText);
            return new dialogs.AlertInfoTreeViewDialog(this, {
                res_model: 'alert.info',
                domain: [
                    ['kpi_id', '=', kpi_id]
                ],
                context: {
                    'kpi_id': kpi_id,
                    'search_default_active_self_created': 1,
                    'active_test': false
                },
                title: _t('Alerts for ' + name_elem),
                title_create: _t('Alert for ' + name_elem),
                initial_ids: ids ? _.map(ids, function (x) { return x[0]; }) : undefined,
                initial_view: view,
                disable_multiple_selection: false,
                on_selected: function (records) {
                    // var ajax = odoo.__DEBUG__.services['web.ajax'];
                    //
                    // ajax.jsonpRpc('/web/dataset/call_kw', 'call', {
                    //     model: 'alert.info',
                    //     method: 'call_create_kpi_alert',
                    //     args: [kpi_id, records[0].id],
                    //     kwargs: {}
                    // }).then(function (result) {
                    //     if (result.res == 0) {
                    //         if (result.error_msg){
                    //         }
                    //         else{
                    //             self.do_action({"type":"ir.actions.act_window_close"});
                    //         }
                    //     } else {
                    //         var options = {};
                    //         options.on_close = function () {
                    //             self.click_alert_bell_btn(event)
                    //         };
                    //         self.do_action(result.action, options)
                    //     }
                    // });

                    var self = this;

                    var dialog = new dialogs.AlertInfoFormViewDialog(this, _.extend({}, records, {
                        // on_saved: function (record) {
                        //     var values = [{
                        //         id: record.res_id,
                        //         display_name: record.data.display_name || record.data.name,
                        //     }];
                        //     self.on_selected(values);
                        // },
                    })).open();
                    if (self.title_create !== undefined){
                        dialog.title = self.title_create;
                    }
                    dialog.on('closed', this, function (){
                        var options = $.extend({}, self.options);
                        var tree_dialog = new dialogs.AlertInfoTreeViewDialog(self.parent, options);
                        self.close();
                        tree_dialog.open();
                        // return tree_dialog
                    });
                    // return dialog;
                }
            }).open();
        },

        reinitialize: function (value) {
            this.isDirty = false;
            this.floating = false;
            return value;
        },

    });
    return HeaderKPIsRenderer;
});
