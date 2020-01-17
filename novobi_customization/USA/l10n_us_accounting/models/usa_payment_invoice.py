# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ..utils.utils import has_multi_currency_group


class USAPaymentInvoice(models.Model):
    _name = 'usa.payment.invoice'
    _description = 'Payment Invoice'
    _rec_name = 'account_move_line_id'

    payment_id = fields.Many2one('account.payment')
    payment_type = fields.Selection(related='payment_id.payment_type')
    partner_id = fields.Many2one('res.partner', related='payment_id.partner_id')
    destination_account_id = fields.Many2one('account.account', related='payment_id.destination_account_id')
    currency_id = fields.Many2one(related='payment_id.currency_id')
    has_multi_currency_group = fields.Boolean(compute='_get_has_multi_currency_group')

    account_move_line_id = fields.Many2one('account.move.line')
    invoice_id = fields.Many2one('account.invoice', related='account_move_line_id.invoice_id')

    date_invoice = fields.Date('Invoice Date', related='invoice_id.date_invoice')
    date_due = fields.Date('Due Date', compute='_get_amount_residual', store=True)

    amount_total = fields.Monetary('Total', compute='_get_amount_residual', store=True)
    residual = fields.Monetary('Amount Due', compute='_get_amount_residual', store=True)

    payment = fields.Monetary('Payment')

    @api.onchange('partner_id')
    def _onchange_partner(self):
        """
        Run when add new open invoice to payment.
        :return: domain for available invoices to add.
        """
        if self.partner_id:
            return {
                'domain': {'account_move_line_id': [('id', 'in', self.payment_id.available_move_line_ids.ids)]},
            }

    @api.depends('account_move_line_id', 'account_move_line_id.balance',
                 'account_move_line_id.amount_residual', 'account_move_line_id.date_maturity',
                 'invoice_id', 'invoice_id.date_due')
    def _get_amount_residual(self):
        for record in self:
            if record.account_move_line_id:
                record.date_due = record.invoice_id.date_due if record.invoice_id \
                    else record.account_move_line_id.date_maturity
                if record.account_move_line_id.currency_id:
                    record.amount_total = abs(record.account_move_line_id.amount_currency)
                    record.residual = abs(record.account_move_line_id.amount_residual_currency)
                else:
                    record.amount_total = abs(record.account_move_line_id.balance)
                    record.residual = abs(record.account_move_line_id.amount_residual)

    @api.depends('account_move_line_id')
    def _get_has_multi_currency_group(self):
        for record in self:
            if has_multi_currency_group(self):
                record.has_multi_currency_group = True

    @api.onchange('account_move_line_id')
    def _onchange_account_move(self):
        if self.account_move_line_id:
            self.payment = self.residual

    @api.onchange('payment')
    def _onchange_payment_amount(self):
        if self.payment <= 0 and self.account_move_line_id:
            raise ValidationError(_('Please enter an amount is greater than 0'))

        if self.payment > self.residual:
            self.payment = self.residual

    @api.constrains('payment')
    def _check_payment_amount(self):
        for record in self:
            if record.payment <= 0:
                raise ValidationError(_('Payment Amount must be greater than 0'))

    @api.constrains('residual')
    def _check_residual_amount(self):
        for record in self:
            # ctx to not remove the line when register payment from invoice
            if record.payment_id.state == 'draft' and self.env.context.get('usa_reconcile', False) is False:
                if record.residual == 0 and record.id:
                    record.unlink()
                elif record.payment > record.residual:
                    record.write({'payment': record.residual})
