# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    @api.multi
    def button_cancel(self):
        res = super().button_cancel()
        model_id = self.env['ir.model'].sudo().search([('model', '=', self._name)], limit=1)
        tracking_rule = self.env['audit.trail.rule'].sudo().search(
            [('model_id', '=', model_id.id), ('state', '=', 'confirmed')], limit=1)
        if tracking_rule:
            old_values = {
                'values': {'state': 'Posted'},
                'rule': tracking_rule,
                'model': model_id,
            }
            new_values = {
                'values': {'state': 'Draft'},
                'rule': tracking_rule,
                'model': model_id,
            }
            for move in self:
                self.env['audit.trail.rule'].sudo(self.env.uid).create_audit_trail_log('write', move,
                                                                                       {move.id: old_values},
                                                                                       {move.id: new_values})
        return res
