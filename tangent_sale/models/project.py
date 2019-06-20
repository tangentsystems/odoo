# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = 'project.task'

    delivered_date = fields.Date('Delivered Date')
    invoice_id = fields.Many2one('account.invoice', ondelete='set null', string='Invoice #', compute='_compute_invoice_id', readonly=True, store=True)

    @api.multi
    @api.depends('sale_line_id', 'sale_line_id.invoice_lines', 'delivered_date')
    def _compute_invoice_id(self):
        for task in self:
            if task.delivered_date and task.sale_line_id:
                if not task.sale_line_id.invoice_lines and task.sale_line_id.invoice_status == 'to_invoice':
                    task.sale_line_id.sudo()._write({'qty_delivered': 1.0})
                    inv = self.env['account.invoice'].create({
                        'partner_id': task.sale_line_id.order_id.partner_invoice_id.id or task.sale_line_id.order_id.partner_id.id,
                    })
                    inv_line_id = self.env['account.invoice.line'].create(
                        task.sale_line_id.invoice_line_create_vals(inv.id, 1.0)
                    )
                if task.sale_line_id.invoice_lines:
                    task.invoice_id = task.sale_line_id.invoice_lines[0].invoice_id
        
