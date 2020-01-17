# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class PaymentDeposit(models.Model):
    _inherit = 'account.payment'

    sale_deposit_id = fields.Many2one('sale.order', 'Sale Order',
                                      help='Is this deposit made for a particular Sale Order?')

    @api.onchange('partner_id')
    def _onchange_partner_sale_id(self):
        if self.payment_type == 'inbound':
            return self._onchange_partner_order_id('sale_deposit_id', ['sale'])

    @api.multi
    def post(self):
        # Check one last time before Validate. Not gonna happen.
        self._validate_order_id('sale_deposit_id', 'Sale Order')
        return super(PaymentDeposit, self).post()
