# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'

    asset_threshold = fields.Monetary("Asset Threshold", related='company_id.asset_threshold')

    @api.multi
    def validate(self):
        for rec in self:
            if float_compare(rec.value, rec.asset_threshold, precision_digits=rec.currency_id.decimal_places) < 0:
                raise UserError(
                    _("Gross value must be greater than or equal to asset threshold (%.2f)" % (rec.asset_threshold)))
        return super(AccountAssetAsset, self).validate()
