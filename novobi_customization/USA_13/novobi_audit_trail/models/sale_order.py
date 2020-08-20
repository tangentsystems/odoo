# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.model
    def _get_tracking_fields(self):
        return ['name', 'state', 'partner_id', 'partner_invoice_id', 'partner_shipping_id', 'sale_order_template_id',
                'date_order', 'payment_term_id', 'order_line', 'amount_total', 'amount_tax', 'amount_untaxed']
