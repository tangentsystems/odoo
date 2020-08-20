# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.misc import formatLang


class BillableExpenses(models.Model):
    _name = 'billable.expenses'
    _description = 'Billable Expenses'
    _rec_name = 'description'

    bill_id = fields.Many2one('account.invoice')
    bill_line_id = fields.Many2one('account.invoice.line')  # expense created from a bill line
    description = fields.Text('Description')
    bill_date = fields.Date('Date')

    amount = fields.Monetary('Amount')
    amount_markup = fields.Monetary('Markup (Amount)', default=0)
    amount_markup_percentage = fields.Float('Markup (%)', default=0)
    amount_total = fields.Monetary('Total Amount', compute='_compute_amount_total')

    currency_id = fields.Many2one('res.currency', compute='_compute_company_id', store=True, string='Expense Currency')
    company_id = fields.Many2one('res.company', compute='_compute_company_id', store=True)
    customer_id = fields.Many2one('res.partner', 'Customer')

    invoice_line_id = fields.Many2one('account.invoice.line')  # expense added to an invoice line
    is_outstanding = fields.Boolean('Outstanding', compute='_get_outstanding_state', store=True)

    # Express in Invoice currency
    invoice_currency_id = fields.Many2one('res.currency', string='Invoice Currency')
    amount_currency = fields.Monetary('Amount Currency', compute='_get_amount_currency', store=True)

    # for report
    source_document = fields.Char('Source Document', compute='_compute_company_id', store=True)
    supplier_id = fields.Many2one('res.partner', 'Supplier', compute='_compute_company_id', store=True)

    @api.depends('amount', 'amount_markup', 'amount_markup_percentage')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = record.amount * (record.amount_markup_percentage + 100)/100 + record.amount_markup

    @api.depends('invoice_line_id', 'invoice_line_id.invoice_id.state')
    def _get_outstanding_state(self):
        for record in self:
            if not record.invoice_line_id or (record.invoice_line_id and
                                              record.invoice_line_id.invoice_id.state == 'draft'):
                record.is_outstanding = True
            else:
                record.is_outstanding = False

    @api.depends('bill_id')
    def _compute_company_id(self):
        for record in self:
            bill = record.bill_id
            if bill:
                record.source_document = bill.number
                record.supplier_id = bill.partner_id
                record.currency_id = bill.currency_id
                record.company_id = bill.company_id

    @api.depends('amount_total', 'currency_id', 'invoice_currency_id')
    def _get_amount_currency(self):
        for record in self:
            if record.invoice_currency_id:
                record.amount_currency = record.currency_id._convert(record.amount_total, record.invoice_currency_id,
                                                                     record.company_id, fields.Date.today())
            else:
                record.amount_currency = record.amount_total

    def _get_log_msg(self, vals):
        current_customer = self.customer_id
        current_amount = formatLang(self.env, self.amount_total, currency_obj=self.currency_id)

        new_amount = vals.get('amount_total', None)
        new_customer = vals.get('customer_id', None)

        msg = 'Billable expense {} {} '.format(self.description, current_amount)
        separate = ''

        if new_customer is not None:
            new_customer = self.env['res.partner'].browse(new_customer)
            if not new_customer:
                msg += 'removed'
            else:
                customer_link = '<a href=javascript:void(0) data-oe-model=res.partner data-oe-id={}>{}</a>' \
                    .format(new_customer.id, new_customer.name)
                if not current_customer:  # assign
                    msg += 'assigned to {}'.format(customer_link)
                else:  # re-assign
                    msg += 're-assigned to {}'.format(customer_link)
            separate = ', '

        if new_amount is not None:
            formatted_amount = formatLang(self.env, new_amount, currency_obj=self.currency_id)
            msg += separate + 'Total Amount changed to {}'.format(formatted_amount)

        return msg

    def _log_message_expense(self, vals):
        """
        Split into different function so we can inherit purchase_billable_expense
        """
        for record in self:
            msg = record._get_log_msg(vals)
            record.bill_id.message_post(body=msg, subtype='account_billable_expense.mt_billable_expense')

    @api.multi
    def write(self, vals):
        if 'customer_id' in vals:
            vals['invoice_line_id'] = False  # reassign expense for another customer

        if 'customer_id' in vals or 'amount_total' in vals:
            self._log_message_expense(vals)

        res = super(BillableExpenses, self).write(vals)

        return res
