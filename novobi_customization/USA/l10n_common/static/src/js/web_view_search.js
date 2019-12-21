odoo.define('l10n_us_accounting.SearchViewExtend', function (require) {
    'use strict';

    var SearchView = require('web.SearchView');

    SearchView.include({
        start: function () {
            var res = this._super.apply(this, arguments);
            if (!this.visible_filters) {
                this.$('.o_searchview_more').click();
            }
            return res;
        }
    });
});