odoo.define('l10n_common.FreezeListViewHeader', function (require) {
    'use strict';

    var ListRenderer = require('web.ListRenderer');
    var field_utils = require('web.field_utils');
    var dom = require('web.dom');
    var FIELD_CLASSES_EXTEND = {
        float: 'o_list_number',
        integer: 'o_list_number',
        monetary: 'o_list_number',
        text: 'o_list_text',
        boolean: 'o_checkbox'
    };

    ListRenderer.include({
        _renderView: function () {
            var self = this;
            return this._super.apply(this, arguments).done(function () {
                function do_freeze () {
                    self.$el.find('table.o_list_view').each(function () {
                        $(this).stickyTableHeaders({scrollableArea: scrollArea});
                    });
                }
                var attrs = self.arch.attrs;
                if (!attrs.noStickyHeader && attrs.string !== '__noStickyHeader__') {
                    var scrollArea = $('.o_content')[0];
                    var isListView = self.$el.find('table.o_list_view').length == 1;
                    if (isListView) { // this is a list view
                        do_freeze();
                        $(window).unbind('resize', do_freeze).bind('resize', do_freeze);
                    }
                }
            });
        },

        /**
         * NOTES: Override this method to render boolean field. We just add an boolean field in model to render a checkbox.
         * Please don't use the checkbox for concurrent update. This is restricted by Odoo.
         *
         * Render a cell for the table. For most cells, we only want to display the
         * formatted value, with some appropriate css class. However, when the
         * node was explicitely defined with a 'widget' attribute, then we
         * instantiate the corresponding widget.
         *
         * @private
         * @param {Object} record
         * @param {Object} node
         * @param {integer} colIndex
         * @param {Object} [options]
         * @param {Object} [options.mode]
         * @param {Object} [options.renderInvisible=false]
         *        force the rendering of invisible cell content
         * @param {Object} [options.renderWidgets=false]
         *        force the rendering of the cell value thanks to a widget
         * @returns {jQueryElement} a <td> element
         */
        _renderBodyCell: function (record, node, colIndex, options) {
            var tdClassName = 'o_data_cell';
            if (node.tag === 'button') {
                tdClassName += ' o_list_button';
            } else if (node.tag === 'field') {
                var typeClass = FIELD_CLASSES_EXTEND[this.state.fields[node.attrs.name].type]; // We just customize this line
                if (typeClass) {
                    tdClassName += (' ' + typeClass);
                }
                if (node.attrs.widget) {
                    tdClassName += (' o_' + node.attrs.widget + '_cell');
                }
            }
            var $td = $('<td>', {class: tdClassName});

            // We register modifiers on the <td> element so that it gets the correct
            // modifiers classes (for styling)
            var modifiers = this._registerModifiers(node, record, $td, _.pick(options, 'mode'));
            // If the invisible modifiers is true, the <td> element is left empty.
            // Indeed, if the modifiers was to change the whole cell would be
            // rerendered anyway.
            if (modifiers.invisible && !(options && options.renderInvisible)) {
                return $td;
            }

            if (node.tag === 'button') {
                return $td.append(this._renderButton(record, node));
            } else if (node.tag === 'widget') {
                return $td.append(this._renderWidget(record, node));
            }
            if (node.attrs.widget || (options && options.renderWidgets)) {
                var $el = this._renderFieldWidget(node, record, _.pick(options, 'mode'));
                this._handleAttributes($el, node);
                return $td.append($el);
            }
            var name = node.attrs.name;
            var field = this.state.fields[name];
            var value = record.data[name];
            var formattedValue;
            if (!this.editable || !node.attrs.is_boolean_editable) {
                formattedValue = field_utils.format[field.type](value, field, {
                    data: record.data,
                    escape: true,
                    isPassword: 'password' in node.attrs,
                });
            } else {
                formattedValue = this._formatBooleanEnable(value, field, {
                    data: record.data,
                    escape: true,
                    isPassword: 'password' in node.attrs,
                });
            }

            this._handleAttributes($td, node);
            return $td.html(formattedValue);
        },

        _formatBooleanEnable: function (value, field, options) {
            if (options && options.forceString) {
                return value ? _t('True') : _t('False');
            }
            return dom.renderCheckbox({
                prop: {
                    checked: value // In this method, we will remove disable property
                }
            });
        }
    })
});
