# -*- coding: utf-8 -*-

from odoo import models, api, fields


class AccountRecordEndingBalance(models.TransientModel):
    _name = 'account.record.ending.balance'
    _description = 'Record Ending Balance'

    options = fields.Selection([
        ('create_purchase_receipt', 'Record payment'),
        ('create_vendor_bill', 'Record a bill then pay later'),
        ('open_report', 'Do it later'),
    ], string='Status', default='create_purchase_receipt')

    bank_reconciliation_data_id = fields.Many2one('account.bank.reconciliation.data')
    currency_id = fields.Many2one('res.currency',
                                  readonly=True, default=lambda self: self.env.user.company_id.currency_id)
    ending_balance = fields.Monetary('Ending Balance')
    vendor_id = fields.Many2one('res.partner', domain=[('supplier', '=', True)])
    payment_journal_id = fields.Many2one('account.journal', domain=[('type', '=', 'bank')])

    @api.onchange('options')
    def _onchange_options(self):
        self.payment_journal_id = False

    @api.multi
    def apply(self):
        self.ensure_one()
        if self.options == 'open_report':
            action = self.env.ref('l10n_us_accounting.action_bank_reconciliation_data_report_form').read()[0]
            action['res_id'] = self.bank_reconciliation_data_id.id
            return action

        if self.options == 'create_purchase_receipt':
            line_vals = {
                'name': 'Credit card expense',
                'account_id': self.bank_reconciliation_data_id.journal_id.default_credit_account_id.id,
                'quantity': 1,
                'price_unit': (-self.ending_balance)
            }
            receipt = self.env['account.voucher'].sudo().with_context({'voucher_type': 'purchase'}).create({
                'voucher_type': 'purchase',
                'partner_id': self.vendor_id.id,
                'pay_now': 'pay_now',
                'account_id': self.vendor_id.property_account_payable_id.id,
                'payment_journal_id': self.payment_journal_id.id,
                'account_date': fields.Date.today(),
                'date': fields.Date.today(),
                'line_ids': [(0, 0, line_vals)]
            })
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.voucher',
                'views': [[False, 'form']],
                'res_id': receipt.id,
                'target': 'main'
            }

        if self.options == 'create_vendor_bill':
            line_vals = {
                'name': 'Credit card expense',
                'account_id': self.bank_reconciliation_data_id.journal_id.default_credit_account_id.id,
                'quantity': 1,
                'price_unit': (-self.ending_balance)
            }
            bill = self.env['account.invoice'].sudo().with_context({'type': 'in_invoice'}).create({
                'partner_id': self.vendor_id.id,
                'date_invoice': fields.Date.today(),
                'invoice_line_ids': [(0, 0, line_vals)]
            })
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.invoice',
                'views': [[False, 'form']],
                'res_id': bill.id,
                'target': 'main'
            }
