# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = 'project.task'

    delivered_date = fields.Date('Delivered Date')
    invoice_id = fields.Many2one('account.invoice', ondelete='set null', string='Invoice #')

    # @api.multi
    # @api.depends('sale_line_id', 'sale_line_id.invoice_lines', 'delivered_date')
    # def _compute_invoice_id(self):
    #     for task in self:
    #         if task.delivered_date and task.sale_line_id:
    #             if not task.sale_line_id.invoice_lines and task.sale_line_id.invoice_status == 'to_invoice':
    #                 task.sale_line_id.sudo()._write({'qty_delivered': 1.0})
    #                 inv = self.env['account.invoice'].create({
    #                     'partner_id': task.sale_line_id.order_id.partner_invoice_id.id or task.sale_line_id.order_id.partner_id.id,
    #                 })
    #                 inv_line_id = self.env['account.invoice.line'].create(
    #                     task.sale_line_id.invoice_line_create_vals(inv.id, 1.0)
    #                 )
    #             if task.sale_line_id.invoice_lines:
    #                 task.invoice_id = task.sale_line_id.invoice_lines[0].invoice_id

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
                if sale_line.invoice_status == 'to invoice':
                    inv_id = self.env['account.invoice'].create({
                        'partner_id': sale_line.order_id.partner_invoice_id.id or sale_line.order_id.partner_id.id,
                    })
                    inv_line_id = self.env['account.invoice.line'].create(
                        sale_line.invoice_line_create_vals(inv_id.id, 1.0)
                    )
                        
            task.invoice_id = inv_id
    
    @api.multi
    def write(self, vals):
        res = super(ProjectTask, self).write(vals)
        if vals.get('delivered_date'):
            for task in self:
                task.assign_task_invoice_id()
        return res
    
        
