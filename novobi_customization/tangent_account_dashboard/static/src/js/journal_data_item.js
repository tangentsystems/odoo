odoo.define("tangent_account_dashboard.journal_data_item", function (require) {
    var fieldRegistry = require('web.field_registry');

    var JournalData = fieldRegistry.get('journal_data');

    JournalData.include({
        _render_chart: function (parent, data, data_type, extra_graph_setting) {
            if (extra_graph_setting && extra_graph_setting.normal_value) {
                this.currency_symbol = '';
            }
            return this._super.apply(this, arguments);
        },
    });
});