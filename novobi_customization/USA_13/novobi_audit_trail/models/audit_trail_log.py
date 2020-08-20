# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import models, fields, api, _


class AuditTrailLog(models.Model):
    _name = 'audit.trail.log'
    _description = 'Audit Log'

    name = fields.Char(string='Name', required=True, copy=False, readonly=True,
                       index=True, default=lambda self: _('New Audit Log'))
    rule_id = fields.Many2one('audit.trail.rule', string='Audit Rule', required=True, ondelete='cascade')
    model_id = fields.Many2one('ir.model', string='Tracking Model', required=True, ondelete='cascade')
    res_id = fields.Integer(string='Resource ID')
    res_name = fields.Char(string='Resource Name')
    res_create_date = fields.Datetime(string='Created Date')
    res_partner_id = fields.Many2one('res.partner', string='Partner')
    res_field_name = fields.Char(string='Changed Field')
    res_old_value = fields.Text(string='Old Value')
    res_new_value = fields.Text(string='New Value')
    author_id = fields.Many2one('res.users', string='User')
    operation = fields.Selection(string='Operation',
                                 selection=[('create', 'Create'), ('read', 'Read'), ('write', 'Edit'),
                                            ('unlink', 'Delete')], required=True)
    create_date = fields.Datetime(string='Date Changed')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New Audit Log')) == _('New Audit Log'):
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('audit_trail_log') or _('New Audit Log')
        res = super().create(vals)
        return res
    
    def action_open_all_logs(self):
        self.ensure_one()
        action = self.env.ref('novobi_audit_trail.action_audit_trail_log_tree').read()[0]
        action['domain'] = [('res_id', '=', self.res_id)]
        return action
