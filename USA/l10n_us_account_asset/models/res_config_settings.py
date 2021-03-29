# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class ResConfigSettingsUSA(models.TransientModel):
    _inherit = 'res.config.settings'

    asset_threshold = fields.Monetary("Asset Threshold", related='company_id.asset_threshold', readonly=False)
