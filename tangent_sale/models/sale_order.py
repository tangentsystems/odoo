# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    parent_task_id = fields.Many2one('project.task', ondelete='set null', string='Parent Task')

    @api.multi
    @api.onchange('parent_task_id')
    def onchange_parent_task_id(self):
        for order in self.filtered('parent_task_id'):
            for sol in order.order_line.filtered('is_service'):    
                sol.parent_task_id = order.parent_task_id


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    parent_task_id = fields.Many2one('project.task', ondelete='set null', string='Parent Task')
    task_name = fields.Char('Task Name')

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.order_id and self.is_service and not self.is_expense:
            self.update({
                'parent_task_id': self.order_id.parent_task_id.id,
                'task_name': self.product_id.task_name,
            })
        return res

    def _timesheet_create_task_prepare_values(self, project):
        vals = super(SaleOrderLine, self)._timesheet_create_task_prepare_values(project)
        vals.update({
            'name': '{}: {}'.format(self.parent_task_id.name, self.task_name) if self.parent_task_id and self.task_name else vals.get('name'),
            'parent_id': self.parent_task_id.id,
            'overwrite_subtask_implied': True,
        })
        return vals

    def _check_ordered_qty(self, qty=1.0):
        self.ensure_one()
        return float_compare(self.product_uom_qty, qty, precision_rounding=self.product_uom.rounding) == 0

