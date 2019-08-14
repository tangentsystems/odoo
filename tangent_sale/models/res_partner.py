# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    multiline_invoice = fields.Boolean('Multi-line Invoice')

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        if not self.parent_id:
            return
        res = super(ResPartner, self).onchange_parent_id()
        if not res.get('value'):
            res['value'] = {}
        res['value'].update({'multiline_invoice': self.parent_id.multiline_invoice})
        return res
    
    
