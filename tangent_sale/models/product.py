# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTaskType(models.Model):
    _name = 'product.task.type'
    _description = 'Product Task Type'

    name = fields.Char('Name')

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # task_name = fields.Char('Task Name')
    task_type_id = fields.Many2one('product.task.type', ondelete='set null', string='Task Type')
