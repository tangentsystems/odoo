# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrModel(models.Model):
    _inherit = 'ir.model'

    search_by_field_ids = fields.Many2many(
        'ir.model.fields',
        'search_model_fields_rel',
        'model_id',
        'field_id'
    )
