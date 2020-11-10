# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProjectSite(models.Model):
    _name = 'project.site'
    _description = 'Site'

    name = fields.Char('Name')


class ProjectTask(models.Model):
    _inherit = 'project.task'

    task_type_id = fields.Many2one('product.task.type', ondelete='set null', string='Task Type', readonly=True)
    delivered_date = fields.Date('Delivered Date')
    invoice_id = fields.Many2one('account.invoice', ondelete='set null', string='Invoice #')

    overwrite_subtask_implied = fields.Boolean('Overwrite Default Parent', help='A technical field to overwrite the default behavior of customer, email_from and sale order line on subtask being replaced by those on the parent task.')

    def assign_task_invoice_id(self):
        self.ensure_one()
        task, inv_id = self, False
        if task.sale_line_id and not task.invoice_id:
            sale_line = task.sudo().sale_line_id
            # if there is exsiting invoice
            if sale_line.invoice_lines:
                inv_id = sale_line.invoice_lines[0].invoice_id
            else:
                if sale_line._check_ordered_qty() and sale_line.qty_delivered != 1.0:
                    sale_line.qty_delivered = 1.0
                if sale_line.invoice_status == 'to invoice' and not sale_line.order_id.multiline_invoice:
                    inv_id = self.env['account.invoice'].create(
                        sale_line.order_id._prepare_invoice()
                    )
                    inv_line_id = self.env['account.invoice.line'].create(
                        sale_line.invoice_line_create_vals(inv_id.id, 1.0)
                    )
                        
            task.invoice_id = inv_id

    # @api.multi
    # @api.onchange('parent_id')
    # def onchange_parent_id(self):
    #     for task in self:
    #         if task.parent_id:
    #             task.overwrite_subtask_implied = task.parent_id.overwrite_subtask_implied
    
    def write(self, vals):
        res = super(ProjectTask, self).write(vals)
        if vals.get('delivered_date'):
            for task in self:
                task.assign_task_invoice_id()
        return res

    @api.model
    def _subtask_implied_fields(self):
        res = super(ProjectTask, self)._subtask_implied_fields()
        if self.env.context.get('overwrite_subtask_implied', False) or self.overwrite_subtask_implied:
            res = []
        if self.parent_id and self.parent_id.overwrite_subtask_implied:
            res = ['overwrite_subtask_implied']
        return res 
    
    @api.model
    def create(self, vals):
        # before create let's pass in some context
        if 'overwrite_subtask_implied' not in self.env.context:
            ctx = dict(self.env.context, overwrite_subtask_implied=vals.get('overwrite_subtask_implied', False))
            res = super(ProjectTask, self).with_context(ctx).create(vals)
        else:
            res = super(ProjectTask, self).create(vals)
        return res
        
