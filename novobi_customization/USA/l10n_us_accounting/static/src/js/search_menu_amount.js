odoo.define('l10n_us_accounting.AmountSearchRange', function (require) {
    'use strict';

    var core = require('web.core');
    var search_inputs = require('web.search_inputs');
    var FiltersMenu = require('web.FiltersMenu');
    var QWeb = core.qweb;
    var Dialog = require('web.Dialog');
    var Domain = require('web.Domain');
    var DropdownMenu = require('web.DropdownMenu');

    FiltersMenu.include({
        events: _.extend({}, DropdownMenu.prototype.events, {
            'click .o_add_filter_amount': function (ev) {
                ev.preventDefault();
                this.toggle_custom_filter_menu_amount();
            },
            'click .o_apply_filter_amount': 'commit_search_amount',
            'click .o_add_custom_filter': '_onAddCustomFilterClick',
            'click .o_add_condition': '_appendProposition',
            'click .o_apply_filter': '_onApplyClick',
            ':hover .o_item_option': '_onOptionHover',
        }),
        init: function (parent, filters, fields) {
            this.titleDisplay = 'Amount from A to B';
            this.isNegativeChecking = true;
            var self = this;

            if (parent.filters.length !== 0) {
                _.each(parent.filters[0].filters, function (item) {
                    // Find a widget filter
                    if (item.attrs['help'] === '__widget__') {
                        self.amountSearchRange = true;
                        self.custom_filters_open_amount = false;
                        self.compared_field = item.attrs['name'];

                        var contextVariable = item.attrs['context'];
                        if (contextVariable) {
                            if (contextVariable.hasOwnProperty('is_negative_checking')) {
                                self.isNegativeChecking = contextVariable.is_negative_checking;
                            }

                            if (contextVariable.hasOwnProperty('title_display')) {
                                self.titleDisplay = contextVariable.title_display;
                            }
                        }
                        return;
                    }
                }, self);
            }
            if(this.amountSearchRange === true){filters.shift();}
            this._super(parent, filters, fields);
        },
        start: function () {
            this._super();
            var self = this;

            if(this.amountSearchRange === true){
                this.$menu = this.$('.o_dropdown_menu');
                var amountSearchRange = QWeb.render('AmountSearchRange', {title_display: self.titleDisplay});
                this.$menu.prepend(amountSearchRange);
            }

            this.$add_filter_amount = this.$('.o_add_filter_amount');
            this.$apply_filter_amount = this.$('.o_apply_filter_amount');
            this.$add_filter_menu_amount = this.$('.o_add_filter_menu_amount');

            // Open search by arrange by default
            this.$('.o_add_filter_amount').click();
        },
        toggle_custom_filter_menu_amount: function (is_open) {
            // KEEP FOR FUTURE REFERENCE
            //  var self = this;
            // this.custom_filters_open_amount = !_.isUndefined(is_open) ? is_open : !this.custom_filters_open_amount;
            // var def;
            // if (this.custom_filters_open_amount && !this.propositions_amount.length) {
            //     def = this.append_proposition_amount();
            // }
            // this.$apply_filter_amount.prop('disabled', false);
            // $.when(def).then(function () {
            //     self.$add_filter_amount
            //         .toggleClass('o_closed_menu_amount', !self.custom_filters_open_amount)
            //         .toggleClass('o_open_menu', self.custom_filters_open_amount);
            //     self.$add_filter_menu_amount.toggle(self.custom_filters_open_amount);
            // });

            var self = this;
            this.custom_filters_open_amount = !_.isUndefined(is_open) ? is_open : !this.custom_filters_open_amount;
            if (this.custom_filters_open_amount) {
                this.$apply_filter_amount.prop('disabled', false);
            }
            $.when(undefined).then(function () {
                self.$add_filter_amount
                    .toggleClass('o_closed_menu_amount', !self.custom_filters_open_amount)
                    .toggleClass('o_open_menu', self.custom_filters_open_amount);
                self.$add_filter_menu_amount.toggle(self.custom_filters_open_amount);
            });
        },

        validate_value: function (value, name) {
            if (!$.isNumeric(value)) {
                this._showErrorMessage(name + ' value must be a valid number');
                return false;
            }

            if (this.isNegativeChecking && value < 0) {
                this._showErrorMessage(name + ' value must not be less than 0.0');
                return false;
            }

            return true;
        },

        commit_search_amount: function () {
            var self = this;
            var min = parseFloat(this.$('#min_val').val());
            if (!this.validate_value(min, 'Min')) {
                return;
            }

            var max = parseFloat(this.$('#max_val').val());
            if (!this.validate_value(max, 'Max')) {
                return;
            }

            if (max < min) {
                this._showErrorMessage('Max value must be greater than Min value');
                return;
            }

            var filters = [{
                'attrs': {
                    'domain': [
                        [this.compared_field, '<=', max],
                        [this.compared_field, '>=', min]
                    ],
                    'modifiers': {},
                    'string': 'Amount from "' + min.toString() + '" to "' + max.toString() + '"'
                },
                'children': [],
                'tag': 'filter'
            }];

            // var filters_widgets = _.map(filters, function (filter) {
            //         return new search_inputs.Filter(filter, this);
            //     }),
            //     filter_group = new search_inputs.FilterGroup(filters_widgets, this.searchview),
            //     facets = filters_widgets.map(function (filter) {
            //         return filter_group.make_facet([filter_group.make_value(filter)]);
            //     });
            _.each(filters, function (filter) {
                filter.attrs.domain = Domain.prototype.arrayToString(filter.attrs.domain);
            });
            var groupId = _.uniqueId('__group__');
            var data = [];
            filters.forEach(function (filter) {
                var filterName = _.uniqueId('__filter__');
                var filterItem = {
                    itemId: filterName,
                    description: filter.attrs.string,
                    groupId: groupId,
                    isActive: true,
                };
                self._prepareItem(filterItem);
                data.push({
                    itemId: filterName,
                    groupId: groupId,
                    filter: filter,
                });
                self.items.push(filterItem);
            });
            this.trigger_up('new_filters', data);
            // keep for later improvement
            // filter_group.insertBefore(this.$add_filter_amount);
            // $('<li class="divider"/>').insertBefore(this.$add_filter_amount);
            // this.searchview.query.add(facets, {silent: true});
            // this.searchview.query.trigger('reset');
            this.toggle_custom_filter_menu_amount(true);
        },

        _showErrorMessage: function (message) {
            new Dialog(this, {
                title: 'Validation error!',
                size: 'medium',
                $content: $('<div>').html('<p>' + message + '<p/>')
            }).open();
        },

        _renderMenuItems: function () {
            var newMenuItems = QWeb.render('DropdownMenu.MenuItems', {widget: this});
            this.$el.find('.o_menu_item, .dropdown-divider[data-removable="1"]').remove();
            if(this.amountSearchRange === true){
                this.$('.o_add_filter_menu_amount').after($(newMenuItems));
            } else {
                this.$('.o_dropdown_menu').prepend($(newMenuItems));
            }
        }
    });
});

