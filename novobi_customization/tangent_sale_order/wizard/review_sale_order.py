# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################
from odoo import models, fields, api, _


class SalesOrder(models.TransientModel):
    _name = 'review.sale.order'
    _description = 'Review Sales Orders'

    @api.model
    def _default_sale_ids(self):
        if self._context.get('active_ids'):
            return self._context['active_ids']
        return False

    sale_ids = fields.Many2many('sale.order', string='Sales Orders', default=_default_sale_ids)
    state = fields.Selection([
        ("draft_quote", "Draft Quotation"),
        ('draft', 'Quotation'),
        ("ready_quote", "Quotation Ready to Submit")
    ], string='New Status')

    def action_confirm(self):
        applied_sales = self.sale_ids.filtered(lambda x: x.state in ['draft_quote', 'draft', 'ready_quote'])
        applied_sales.write({'state': self.state})
        return True
