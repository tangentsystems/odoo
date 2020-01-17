# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_open(self):
        # Apply deposit from SO in Invoice
        res = super(AccountInvoice, self).action_invoice_open()

        for invoice in self:
            if invoice.type == 'out_invoice':
                sale_order_ids = self.env['sale.order']
                for line in invoice.invoice_line_ids:
                    sale_order_ids += line.sale_line_ids.mapped('order_id')
                deposits = sale_order_ids.mapped('deposit_ids')

                self._reconcile_deposit(deposits, invoice)
        return res
