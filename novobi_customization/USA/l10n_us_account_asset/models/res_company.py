# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    asset_threshold = fields.Monetary("Asset Threshold", default=0, help="Able to create Assets when bill line's total amount is greater than or equal to asset threshold.")
