# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################
from odoo import models, fields, api, _

READONLY_STATES = {'draft_quote': [('readonly', False)],
                   'draft': [('readonly', False)],
                   'ready_quote': [('readonly', False)],
                   'sent': [('readonly', False)]}


class SalesOrder(models.Model):
    _inherit = 'sale.order'

    # Override to add 2 new states
    state = fields.Selection([
        ("draft_quote", "Draft Quotation"),
        ('draft', 'Quotation'),
        ("ready_quote", "Quotation Ready to Submit"),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], default='draft_quote')

    partner_id = fields.Many2one('res.partner', states=READONLY_STATES)
    partner_invoice_id = fields.Many2one('res.partner', states=READONLY_STATES)
    partner_shipping_id = fields.Many2one('res.partner', states=READONLY_STATES)

    date_order = fields.Datetime(states=READONLY_STATES)
    validity_date = fields.Date(states=READONLY_STATES)
    date_order = fields.Datetime(states=READONLY_STATES)
    pricelist_id = fields.Many2one('product.pricelist', states=READONLY_STATES)
    sale_order_option_ids = fields.One2many('sale.order.option', 'order_id', states=READONLY_STATES)

    @api.multi
    def action_review_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def action_por(self):
        return self.write({'state': 'ready_quote'})

    @api.multi
    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel', 'draft', 'ready_quote', 'sent'])
        return orders.write({
            'state': 'draft_quote',
            'signature': False,
            'signed_by': False,
        })

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        # Update ready_quote state
        if self.env.context.get('mark_so_as_sent'):
            self.filtered(lambda o: o.state in ['draft', 'ready_quote']).with_context(tracking_disable=True).write({'state': 'sent'})
        return super(SalesOrder, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)


