# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2019 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    amount_so_remaining = fields.Monetary(string='Unpaid Amount', default=0,
                                          compute="_get_remaining_so_amount", store=True)
    
    @api.depends('amount_total', 'deposit_total', 'deposit_ids', 'invoice_ids')
    def _get_remaining_so_amount(self):
        """
        Calculate the remaining amount of Sale Order
        @return:
        """
        for order in self:
            invoices = order.invoice_ids.filtered(
                lambda i: i.state not in ('draft', 'cancel') and i.type == 'out_invoice')
            total_invoice_amount = sum(invoices.mapped('amount_total'))
            total_deposit_amount = sum(
                order.deposit_ids.filtered(lambda d: d.state not in ('draft', 'cancelled')).mapped(
                    'outstanding_payment'))
            order.update({
                'amount_so_remaining': order.amount_total - total_invoice_amount - total_deposit_amount,
            })
