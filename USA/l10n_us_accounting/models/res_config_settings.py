# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

from ..models.model_const import ACCOUNT_ACCOUNT


class ResConfigSettingsUSA(models.TransientModel):
    _inherit = 'res.config.settings'

    bad_debt_account_id = fields.Many2one(ACCOUNT_ACCOUNT, string='Write Off Account',
                                          related='company_id.bad_debt_account_id', readonly=False,
                                          domain=[('deprecated', '=', False)])
