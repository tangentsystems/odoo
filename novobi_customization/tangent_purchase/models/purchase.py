# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################
from odoo import models, fields, api, _
from odoo.tools import float_compare


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    service_order_line_ids = fields.One2many('purchase.order.line', 'order_id',
                                             string="Service Lines",
                                             domain=[('product_type', '=', 'service')])

    def action_receive_service_products(self):
        self.ensure_one()
        view_id = self.env.ref('tangent_purchase.view_service_purchase_order_line_form').id
        return {
            'name': _('Receive Products'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': self.id,
            'view_id': view_id,
            'target': 'new',
        }

    def button_receive_all(self):
        self.ensure_one()
        service_products = self.order_line.filtered(lambda line: line.product_type == 'service')
        for line in service_products:
            line.qty_received = line.product_qty
        return {'type': 'ir.actions.act_window_close'}

    def button_receive_manual(self):
        return {'type': 'ir.actions.act_window_close'}
