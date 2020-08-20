# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartnerUSA(models.Model):
    _inherit = 'res.partner'

    billable_expenses_ids = fields.One2many('billable.expenses', 'customer_id')
