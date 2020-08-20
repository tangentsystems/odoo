odoo.define('usa.payment', function (require) {
    'use strict';

    var core = require('web.core');
    var field_registry = require('web.field_registry');
    var field_utils = require('web.field_utils');
    var QWeb = core.qweb;

    var AccountPayment = field_registry.get('payment');
    AccountPayment.include({
        _render: function () {
            var self = this;

            var info = JSON.parse(this.value);
            if (!info) {
                this.$el.html('');
                return;
            }
            _.each(info.content, function (k, v) {
                k.index = v;
                k.amount = field_utils.format.float(k.amount, {digits: k.digits});
                if (k.date) {
                    k.date = moment(k.date, 'YYYY/MM/DD').format('MMM DD, YYYY');
                }
            });
            this.$el.html(QWeb.render('ShowPaymentInfoUSA', {
                lines: info.content,
                outstanding: info.outstanding,
                title: info.title,
                type: info.type
            }));

            this.$el.find('i.remove-payment-usa').on('click', self._onRemoveMoveReconcile.bind(self));
            this.$el.find('a.open-payment-usa, a.open_transaction').on('click', self._onOpenPayment.bind(self));
        },

        // Open a Popup with Amount
        _onOutstandingCreditAssign: function (event) {
            var self = this;
            var id = $(event.target).data('id') || false;

            self.do_action({
                name: 'Amount to Apply',
                type: 'ir.actions.act_window',
                res_model: 'account.invoice.partial.payment',
                views: [[false, "form"]],
                target: 'new',
                context: {
                    invoice_id: JSON.parse(this.value).invoice_id,
                    credit_aml_id: id
                }
            }, {
                on_close: function () {
                    self.trigger_up('reload');
                }
            });
        },

        _onOpenPayment: function (event) {
            var self = this;
            var invoiceId = parseInt($(event.target).attr('invoice-id'));
            var paymentId = parseInt($(event.target).attr('payment-id'));
            var moveId = parseInt($(event.target).attr('move-id'));
            var res_model;
            var id;
            if (invoiceId !== undefined && !isNaN(invoiceId)) {
                res_model = "account.invoice";
                id = invoiceId;
            } else if (paymentId !== undefined && !isNaN(paymentId)) {
                res_model = "account.payment";
                id = paymentId;
            } else if (moveId !== undefined && !isNaN(moveId)) {
                res_model = "account.move";
                id = moveId;
            }

            //Open form view of account.move with id = move_id
            if (id) {
                var default_action = {
                    type: 'ir.actions.act_window',
                    res_model: res_model,
                    res_id: id,
                    views: [[false, 'form']],
                    target: 'current'
                };

                if (res_model === 'account.invoice') {
                    this._rpc({
                        model: 'account.invoice',
                        method: 'open_form',
                        args: [id]
                    }).then(function (action) {
                        if (action) {
                            action.res_id = id;
                            self.do_action(action);
                        }
                        else
                            self.do_action(default_action);
                    });
                }
                else if (res_model) {
                    this.do_action(default_action);
                }
            }
        }
    });
});