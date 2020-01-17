# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.
import json
from odoo import api, fields, models, _
from odoo.tools import float_is_zero
import logging


class InvoiceDeposit(models.Model):
    _inherit = 'account.invoice'

    @api.one
    def _get_outstanding_info_JSON(self):
        super(InvoiceDeposit, self)._get_outstanding_info_JSON()

        info = json.loads(self.outstanding_credits_debits_widget)

        if self.state == 'open':
            domain = [('account_id.reconcile', '=', True),
                      ('payment_id.is_deposit', '=', True),
                      ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                      ('reconciled', '=', False),
                      '|', ('amount_residual', '!=', 0.0),
                      ('amount_residual_currency', '!=', 0.0)]

            if self.type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')

            if not info:
                info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)

            currency_id = self.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == self.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        currency = line.company_id.currency_id
                        amount_to_show = currency._convert(abs(line.amount_residual), self.currency_id, self.company_id,
                                                           line.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue

                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'payment_id': line.payment_id.id,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })

                info['title'] = type_payment
                info['type'] = self.type
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True

    @api.multi
    def assign_outstanding_credit(self, credit_aml_id):
        self.ensure_one()
        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if credit_aml.payment_id and credit_aml.payment_id.is_deposit:
            line_to_reconcile = self.env['account.move.line']
            for inv in self:
                line_to_reconcile += inv.move_id.line_ids.filtered(
                    lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))

            register_payment_line = self._create_deposit_payment_entry(credit_aml, line_to_reconcile)
            self.register_payment(register_payment_line)
        else:
            return super(InvoiceDeposit, self).assign_outstanding_credit(credit_aml_id)

    @api.multi
    def _create_deposit_payment_entry(self, payment_line, invoice_lines):
        total_invoice_amount = abs(sum(invoice_lines.mapped('amount_residual')))
        amount = min(total_invoice_amount, abs(payment_line.amount_residual))

        if self.env.context.get('partial_amount', False):
            amount = self.env.context.get('partial_amount')

        company_id = payment_line.company_id
        journal_id = False
        if payment_line.debit > 0:
            journal_id = company_id.vendor_deposit_journal_id
        elif payment_line.credit > 0:
            journal_id = company_id.customer_deposit_journal_id
        if not journal_id:
            journal_id = self.env['account.journal'].search([('type', '=', 'general')], limit=1)

        debit_account, credit_account = self._get_account_side(payment_line, invoice_lines)
        reference = "Deposit to Payment"
        payment_id = payment_line.payment_id

        new_account_move = self.env['account.move'].create({
            'journal_id': journal_id.id,
            'date': payment_line.date,
            'ref': reference,
            'is_deposit': True,
            'line_ids': [(0, 0, {
                'partner_id': payment_line.partner_id.id,
                'account_id': debit_account.id,
                'debit': amount,
                'credit': 0,
                'date': payment_line.date,
                'name': reference,
            }), (0, 0, {
                'partner_id': self.partner_id.id if self.partner_id else False,
                'account_id': credit_account.id,
                'debit': 0,
                'credit': amount,
                'date': payment_line.date,
                'name': reference,
            })],
        })
        new_account_move.post()

        (payment_line + new_account_move.line_ids.filtered(lambda l: l.account_id == payment_line.account_id)).reconcile()
        payment_id.write({'deposit_ids': [(4, new_account_move.id)]})

        return new_account_move.line_ids.filtered(lambda l: l.account_id.internal_type in ('payable', 'receivable'))

    def _get_account_side(self, payment_line, invoice_lines):
        invoice_line = invoice_lines[0]
        debit_account = payment_line.account_id if payment_line.credit > 0 else invoice_line.account_id
        credit_account = payment_line.account_id if payment_line.debit > 0 else invoice_line.account_id

        return debit_account, credit_account

    def _reconcile_deposit(self, deposits, invoice):
        # Helper function to reconcile deposit automatically when confirm Invoice/Bill
        for deposit in deposits:
            move_line = deposit.move_line_ids.filtered(lambda line: line.account_id.reconcile and
                                                                    line.account_id.internal_type != 'liquidity')
            if move_line:
                invoice.assign_outstanding_credit(move_line.id)
