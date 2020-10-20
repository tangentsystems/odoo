# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    parent_task_id = fields.Many2one('project.task', ondelete='set null', string='Parent Task')

    multiline_invoice = fields.Boolean('Multi-line Invoice')
    
    @api.onchange('parent_task_id')
    def onchange_parent_task_id(self):
        for order in self.filtered('parent_task_id'):
            for sol in order.order_line.filtered('is_service'):    
                sol.parent_task_id = order.parent_task_id

    @api.onchange('partner_id')
    def onchange_partner_id_multiline_invoice(self):
        self.ensure_one()
        if self.partner_id:
            self.multiline_invoice = self.partner_id.multiline_invoice


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    parent_task_id = fields.Many2one('project.task', ondelete='set null', string='Parent Task')
    site_id = fields.Many2one('project.site', ondelete='set null', string='Site')
    task_name = fields.Char('Task Name')
    task_type_id = fields.Many2one('product.task.type', ondelete='set null', string='Task Type')

    def _get_task_name(self):
        self.ensure_one()
        return '{}: {}'.format(self.site_id.name, self.product_id.name) if self.product_id and self.site_id else ''
    
    @api.onchange('product_id', 'site_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        # if self.order_id and self.is_service and not self.is_expense:
        self.update({
            'parent_task_id': self.order_id.parent_task_id.id,
            'task_type_id': self.product_id.task_type_id.id,
            'task_name': self._get_task_name(),
        })
        return res

    @api.onchange('product_id', 'parent_task_id')
    def _onchange_parent_task_id(self):
        res = {}
        if self.product_id and self.parent_task_id and self.product_id.project_id != self.parent_task_id.project_id:
            warning_mess = {
                'title': _('Not Same Project'),
                'message' : _('The product belongs to project [{}] while parent task belongs to project [{}].'.format(self.product_id.project_id.display_name, self.parent_task_id.project_id.display_name))
            }
            res = {'warning': warning_mess}
        return res

    
    def _timesheet_create_task_prepare_values(self, project):
        vals = super(SaleOrderLine, self)._timesheet_create_task_prepare_values(project)
        vals.update({
            # 'name': '{}: {}'.format(self.parent_task_id.name, self.task_name) if self.parent_task_id and self.task_name else vals.get('name'),
            'name': self._get_task_name() or vals.get('name'),
            'parent_id': self.parent_task_id.id,
            'task_type_id': self.task_type_id.id,
            'overwrite_subtask_implied': True,  # this means this task's sale order should be the current sale sale's order, not the task's parent's order
        })
        return vals

    def _check_ordered_qty(self, qty=1.0):
        self.ensure_one()
        return float_compare(self.product_uom_qty, qty, precision_rounding=self.product_uom.rounding) == 0

