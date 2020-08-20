# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_open(self):
        # Apply deposit from PO in Invoice
        res = super(AccountInvoice, self).action_invoice_open()

        for invoice in self:
            if invoice.type == 'in_invoice':
                purchase_order_ids = invoice.invoice_line_ids.mapped('purchase_id')
                deposits = purchase_order_ids.mapped('deposit_ids')

                self._reconcile_deposit(deposits, invoice)
        return res
