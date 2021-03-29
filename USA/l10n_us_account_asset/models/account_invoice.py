# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare
class AccountInvoiceUSA(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_open(self):
        for invoice in self:
            for line in invoice.invoice_line_ids:
                if float_compare(line.price_total, line.asset_threshold, precision_digits=line.currency_id.decimal_places) < 0:
                    line.asset_check = False
                    line.asset_category_id = False
        return super(AccountInvoiceUSA, self).action_invoice_open()

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    asset_threshold = fields.Monetary("Asset Threshold", related='company_id.asset_threshold',store=True)
    asset_check = fields.Boolean("Asset Check", compute='_compute_asset_check')

    @api.onchange('asset_threshold','price_total','price_subtotal')
    def _compute_asset_check(self):
        for rec in self:
            if float_compare(rec.price_total, rec.asset_threshold, precision_digits=rec.currency_id.decimal_places) < 0:
                rec.asset_check = False
                rec.asset_category_id = False
            else:
                rec.asset_check = True
