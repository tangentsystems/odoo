# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import models, fields, api, _, modules

DEFAULT_OPERATIONS = ['create', 'write', 'unlink']


class AuditTrailRule(models.Model):
    _name = 'audit.trail.rule'
    _description = 'Audit Rule'
    
    name = fields.Char(string='Name', required=True, default='New Audit Rule')
    model_id = fields.Many2one('ir.model', string='Tracking Model', required=True, ondelete='cascade')
    is_track_create = fields.Boolean(string='Track Create Operation', default=True)
    is_track_write = fields.Boolean(string='Track Edit Operation', default=True)
    is_track_unlink = fields.Boolean(string='Track Delete Operation', default=True)
    state = fields.Selection(string='Status',
                             selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('cancel', 'Cancelled')],
                             required=True, default='draft')
    tracking_field_ids = fields.Many2many('ir.model.fields', string='Tracking Fields')
    is_tracking_all_fields = fields.Boolean("Track All Fields", default=True)
    
    _sql_constraints = [
        ('unique_rule_per_model', 'unique(model_id)', "A tracking model must have only one tracking rule.")]
    
    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.tracking_field_ids.unlink()
    
    def action_confirm_rule(self):
        """
        Set state to `Confirmed` after users click on `Confirm` button
        :return:
        """
        self.update({'state': 'confirmed'})
        self._register_hook()
    
    def action_cancel_rule(self):
        """
        Set state to `Cancelled` after users click on `Cancel` button
        :return:
        """
        self.update({'state': 'cancel'})
    
    def action_set_draft(self):
        """
        Set state to `Draft` after users click on `Set To Draft` button
        :return:
        """
        self.update({'state': 'draft'})
    
    def _register_hook(self):
        """
        Register hook for tracking changes
        :return: TRUE if the model already registered hook, else FALSE
        """
        res = super()._register_hook()
        if not self:
            self = self.env['audit.trail.rule'].search([('state', '=', 'confirmed')])
        return self._is_need_to_patch_default_methods() or res
    
    def _is_need_to_patch_default_methods(self):
        """
        Monkey-patch the default CREATE/WRITE/DELETE methods (if needed) for tracking changes when calling to these methods
        :return: TRUE if it needs to patch at least one of these above default methods, else FALSE
        """
        confirmed_rules = self.filtered(lambda r: r.state == 'confirmed')
        is_patch_default_method = False
        for rule in confirmed_rules:
            tracking_model = self.env[rule.model_id.model].sudo()
            
            for field in ['is_track_create', 'is_track_write', 'is_track_unlink']:
                if getattr(rule, field, False) and not hasattr(tracking_model, field + '_created'):
                    tracking_method = field[field.rfind('_') + 1:]
                    self.env['audit.trail.rule'].sudo()._monkey_patch_method(tracking_model, tracking_method)
                    setattr(type(tracking_model), field + '_created', True)
                    is_patch_default_method = True
            act_view_log = self.env['ir.actions.act_window'].sudo().search(
                [('res_model', '=', 'audit.trail.log'), ('binding_model_id', '=', rule.model_id.id)])
            if not act_view_log:
                rule.create_action_view_audit_log()
        return is_patch_default_method
    
    @api.model
    def _monkey_patch_method(self, tracking_model, method_name):
        """
        Monkey-patch the default CREATE/WRITE/DELETE methods (if needed) for tracking changes when calling to these methods
        :param tracking_model: model object
        :param method_name: name of method
        :return:
        """
        
        @api.model
        def tracking_create_operation(self, vals):
            res = tracking_create_operation.origin(self, vals)
            if isinstance(vals, list):
                keys_list = [list(vals_i.keys()) for vals_i in vals]
            elif isinstance(vals, dict):
                keys_list = [list(vals.keys())]
            else:
                keys_list = []
            new_values = self.env['audit.trail.rule'].sudo().get_tracking_value(res, keys_list)
            self.env['audit.trail.rule'].sudo().create_audit_trail_log('create', res, new_values=new_values)
            return res
        
        def tracking_write_operation(self, vals):
            if isinstance(vals, list):
                keys_list = [list(vals_i.keys()) for vals_i in vals]
            elif isinstance(vals, dict):
                keys_list = [list(vals.keys())]
            else:
                keys_list = []
            old_values = self.env['audit.trail.rule'].sudo().get_tracking_value(self, keys_list)
            res = tracking_write_operation.origin(self, vals)
            new_values = self.env['audit.trail.rule'].sudo().get_tracking_value(self, keys_list)
            self.env['audit.trail.rule'].sudo().create_audit_trail_log('write', self, old_values, new_values)
            return res
        
        def tracking_compute_field_value(self, field):
            """Override computed function for tracking computed fields"""
            if field.store and any(self._ids):
                compute_field = [str(key).replace(self._name + '.', '') for key in list(self._field_computed.keys())]
                keys_list = [compute_field for record in self]
                old_values = self.env['audit.trail.rule'].sudo().get_tracking_value(self._origin, keys_list)
                res = tracking_compute_field_value.origin(self, field)
                new_values = self.env['audit.trail.rule'].sudo().get_tracking_value(self, keys_list)
                self.env['audit.trail.rule'].sudo().create_audit_trail_log('write', self, old_values, new_values)
            else:
                res = tracking_compute_field_value.origin(self, field)
            return res
        
        # def tracking_update_operation(self, values):
        #     if self._origin:
        #         keys_list = []
        #         if isinstance(values, list):
        #             keys_list = [list(vals_i.keys()) for vals_i in values]
        #         elif isinstance(values, dict):
        #             keys_list = [list(values.keys())]
        #         old_values = self.env['audit.trail.rule'].sudo().get_tracking_value(self, keys_list)
        #         res = tracking_update_operation.origin(self, values)
        #         new_values = self.env['audit.trail.rule'].sudo().get_tracking_value(self, keys_list)
        #         self.env['audit.trail.rule'].sudo().create_audit_trail_log('write', self, old_values, new_values)
        #     else:
        #         res = tracking_update_operation.origin(self, values)
        #     return res
        
        def tracking_unlink_operation(self):
            self.env['audit.trail.rule'].sudo().create_audit_trail_log('unlink', self)
            res = tracking_unlink_operation.origin(self)
            return res
        
        tracking_function = False
        if method_name == 'create':
            tracking_function = tracking_create_operation
        elif method_name == 'write':
            tracking_function = tracking_write_operation
            # tracking_model._patch_method('update', tracking_update_operation)
            # setattr(type(tracking_model), 'tracking_update_created', True)
            tracking_model._patch_method('_compute_field_value', tracking_compute_field_value)
            setattr(type(tracking_model), 'tracking_compute_field_created', True)
        elif method_name == 'unlink':
            tracking_function = tracking_unlink_operation
        if tracking_function:
            tracking_model._patch_method(method_name, tracking_function)
    
    def remove_all_patch_methods(self, operation_list=DEFAULT_OPERATIONS, is_delete=False):
        """
        Remove all patched methods (create/write/unlink) to origin
        :return:
        """
        is_need_to_reset = False
        for rule in self:
            tracking_model = self.env[rule.model_id.model].sudo()
            for operation in operation_list:
                if getattr(rule, 'is_track_{}'.format(operation)) and hasattr(getattr(tracking_model, operation), 'origin') and \
                        getattr(tracking_model, 'tracking_{}_created'.format(operation), False):
                    tracking_model._revert_method(operation)
                    delattr(type(tracking_model), 'is_track_{}_created'.format(operation))
                    is_need_to_reset = True
                if operation == 'write':
                    # if hasattr(getattr(tracking_model, 'update'), 'origin') and getattr(tracking_model, 'tracking_update_created', False):
                    #     tracking_model._revert_method('update')
                    #     is_need_to_reset = True
                    if hasattr(getattr(tracking_model, '_compute_field_value'), 'origin') and getattr(tracking_model, 'tracking_compute_field_created', False):
                        tracking_model._revert_method('_compute_field_value')
                        is_need_to_reset = True
        if is_delete:
            act_view_log = self.env['ir.actions.act_window'].sudo().search([('res_model', '=', 'audit.trail.log'), ('binding_model_id', 'in', self.model_id.ids)])
            for act in act_view_log:
                act.unlink()
        if is_need_to_reset:
            modules.registry.Registry(self.env.cr.dbname).signal_changes()
    
    @api.model
    def create_audit_trail_log(self, operation, records, old_values={}, new_values={}):
        """
        Create a log to record the changes with the operation create/write/unlink
        :param operation: create/write/unlink
        :param records: the resource records
        :param old_values: the old values
        :param new_values: the new values
        :return: created log for recording the changes
        """
        created_log = []
        for record in records:
            record = record.sudo()
            # Create log
            rule = new_values.get(record.id) and new_values[record.id].get('rule')
            res_string_fields = self.env['ir.translation'].sudo().get_field_string(record._name)
            res_partner_id = getattr(record, 'partner_id', '')
            audit_log_env = self.env['audit.trail.log'].sudo()
            if operation == 'unlink':
                model_id = self.env['ir.model'].sudo().search([('model', '=', record._name)], limit=1)
                tracking_rule = self.env['audit.trail.rule'].sudo().search(
                    [('model_id', '=', model_id.id), ('state', '=', 'confirmed')], limit=1)
                log_vals = {
                    'rule_id': tracking_rule and tracking_rule.id,
                    'res_name': record.name_get()[0][1],
                    'res_create_date': getattr(record, 'create_date', None),
                    'res_partner_id': res_partner_id and res_partner_id.id,
                    'model_id': self.env['ir.model'].sudo().search([('model', '=', record._name)], limit=1).id,
                    'res_id': record.id,
                    'author_id': self.env.user.id,
                    'operation': operation,
                }
                log = audit_log_env.create(log_vals)
                created_log.append(log)
            else:
                # Track changes
                record_old_values = old_values.get(record.id, {}) and old_values[record.id].get('values', [])
                record_new_values = new_values.get(record.id, {}) and new_values[record.id].get('values', [])
                old_state = record_old_values.get('state', '')
                new_state = record_new_values.get('state', '')
                # Do not track when editing draft/canceled records
                ignore_states = ['draft', 'cancel']
                if not new_state and not old_state and getattr(record, 'state', '') in ignore_states and operation == 'write':
                    continue
                for key in record_new_values.keys():
                    old_value = record_old_values.get(key, '')
                    new_value = record_new_values.get(key, '')
                    if old_value != new_value and (old_value or new_value):
                        # Create log if the change occurs
                        log_vals = {
                            'rule_id': rule and rule.id,
                            'res_name': record.name_get()[0][1],
                            'res_create_date': getattr(record, 'create_date', None),
                            'res_partner_id': res_partner_id and res_partner_id.id,
                            'res_field_name': res_string_fields.get(key, ''),
                            'res_old_value': old_value,
                            'res_new_value': new_value,
                            'model_id': self.env['ir.model'].sudo().search([('model', '=', record._name)], limit=1).id,
                            'res_id': record.id,
                            'author_id': self.env.user.id,
                            'operation': operation,
                        }
                        log = audit_log_env.create(log_vals)
                        created_log.append(log)
        return created_log
    
    @api.model
    def get_tracking_value(self, records, keys_list):
        """
        Get current value of specific fields in the `keys` list
        :param records: records that need to get the value
        :param keys_list: list of the fields names of each record
        :return: dictionary of values
        """
        tracking_dict = {}
        length = len(records)
        if length > len(keys_list):
            for i in range(0, length - len(keys_list)):
                keys_list = keys_list + [keys_list[0]]
        model_id = self.env['ir.model'].sudo().search([('model', '=', records._name)], limit=1)
        tracking_rule = self.env['audit.trail.rule'].sudo().search(
            [('model_id', '=', model_id.id), ('state', '=', 'confirmed')], limit=1)
        if tracking_rule.is_tracking_all_fields:
            tracking_fields = self.env['ir.model.fields'].sudo().search(
                [('model', '=', records._name), ('store', '=', True)])
        else:
            tracking_fields = tracking_rule.tracking_field_ids
        for i in range(0, length):
            record = records[i].sudo()
            keys_i = keys_list[i]
            value_dict = {}
            for key in keys_i:
                changed_fields = tracking_fields.filtered(lambda f: f.name == key)
                changed_field = len(changed_fields) > 1 and changed_fields[0] or changed_fields
                if hasattr(record, key) and changed_field:
                    if changed_field['relation']:
                        value = record[key].name_get()
                        value_dict[key] = '\n'.join([name and name[1] for name in value])
                    elif changed_field['ttype'] == 'selection':
                        selection = self.env[record._name].sudo()._fields[key].selection
                        value_dict[key] = isinstance(selection, list) and dict(selection).get(record[key]) or ''
                    else:
                        value_dict[key] = record[key]
            tracking_dict[record.id] = {
                'values': value_dict,
                'rule': tracking_rule,
                'model': model_id,
            }
        return tracking_dict
    
    def create_action_view_audit_log(self):
        """
        Create new action item in the form view for tracking model to view the audit logs
        :return:
        """
        obj_env = self.env['ir.actions.act_window'].sudo()
        for rule in self:
            domain = "[('model_id', '=', {}), ('res_id', 'in', active_ids)]".format(rule.model_id.id)
            vals = {
                'name': _('Audit Logs'),
                'res_model': 'audit.trail.log',
                'binding_model_id': rule.model_id.id,
                'binding_view_types': 'form',
                'view_mode': 'list,form',
                'domain': domain,
            }
            obj_env.create(vals)
    
    def write(self, vals):
        # Remove tracking operations after user disable it
        operations = DEFAULT_OPERATIONS
        self.remove_all_patch_methods(operation_list=operations)
        res = super().write(vals)
        # Register hook for tracking operations
        self._register_hook()
        return res
    
    def unlink(self):
        # Remove all patched methods to resource models before unlink the rules
        self.remove_all_patch_methods(is_delete=True)
        return super().unlink()

    @api.model
    def create(self, vals):
        if vals.get('name', _('New Audit Rule')) == _('New Audit Rule'):
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code('audit_trail_rule') or _('New Audit Rule')
        res = super().create(vals)
        return res
