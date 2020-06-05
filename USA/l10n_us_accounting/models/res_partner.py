# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.
from ast import literal_eval
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from ..models.model_const import RES_PARTNER, IR_SEQUENCE


class CustomerUSA(models.Model):
    _inherit = 'res.partner'

    country_id = fields.Many2one(default=lambda self: self.env.ref('base.us') and self.env.ref('base.us').id)

    def _get_default_ref(self):
        # generate next sequence manually since sequence doesn't support default func
        sequence_id = self.env.ref('l10n_us_accounting.customer_code')
        next_number = sequence_id.number_next_actual
        sequence_size = sequence_id.padding
        prefix = sequence_id.prefix or ''
        suffix = sequence_id.suffix or ''
        return prefix + '{:0{size}}'.format(next_number, size=sequence_size) + suffix

    @api.constrains('vat')
    def _check_vat_format(self):
        for record in self:
            if record.vat:
                if len(record.vat) != 10 or record.vat[2] != '-':
                    raise ValidationError('EIN is not in the correct format')

                for i in range(len(record.vat)):
                    if i != 2 and not record.vat[i].isnumeric():
                        raise ValidationError('EIN is not in the correct format')

    vat = fields.Char(string='EIN', help='Employer Identification Number')
    ref = fields.Char(string='Code', default=_get_default_ref)

    ar_in_charge = fields.Many2one(string='AR In Charge', comodel_name='res.users')
    type = fields.Selection(selection_add=[('invoice', 'Billing Address')])

    print_check_as = fields.Boolean('Print on check as',
                                    help='Check this box if you want to use a different name on checks.')
    check_name = fields.Char('Name on Check')

    # fields for vendor
    vendor_company_tax_id = fields.Char()
    vendor_individual_tax_id = fields.Char()
    vendor_eligible_1099 = fields.Boolean(string='Vendor Eligible for 1099', default=False)
    print_on_check = fields.Char(string='Print on Check as', default=lambda self: self.name)  # no longer use
    debit = fields.Monetary(store=True)  # override to store
    debit_overdue_amount = fields.Monetary(compute='_debit_overdue_balance_get', string='Overdue Balance', store=True)
    debit_open_balance = fields.Monetary(compute='_debit_overdue_balance_get', string='Open Balance', store=True)

    # fields for customer
    customer_tax_id = fields.Char()
    credit = fields.Monetary(store=True)  # override to store
    overdue_amount = fields.Monetary(compute='_overdue_balance_get', string='Overdue Balance', store=True)
    open_balance = fields.Monetary(compute='_overdue_balance_get', string='Open Balance', store=True)
    num_open_invoices = fields.Integer(compute='_num_open_invoices_get', string='Open Invoices')

    # override
    partner_ledger_label = fields.Char(help='')  # remove help

    @api.onchange('print_check_as')
    def _onchange_print_check_as(self):
        for record in self:
            record.check_name = record.name

    @api.model
    def create(self, vals):
        vals['ref'] = self._get_ref_next_sequence()
        return super(CustomerUSA, self).create(vals)

    @api.model
    def init_ref_value(self):
        for res_partner_record in self.env[RES_PARTNER].search([('ref', '=', None)], order='id'):
            res_partner_record.ref = self._get_ref_next_sequence()

    # switch to store => need to specify dependent fields
    @api.depends('invoice_ids', 'invoice_ids.residual_signed', 'invoice_ids.date_due', 'invoice_ids.state',
                 'child_ids.invoice_ids', 'child_ids.invoice_ids.residual_signed', 'child_ids.invoice_ids.date_due',
                 'child_ids.invoice_ids.state')
    def _credit_debit_get(self):
        if self.ids:
            super(CustomerUSA, self)._credit_debit_get()

    # For Debit (Total Payable)
    def _get_amount_due_from_bill(self, bill_ids):
        overdue_bill_ids = bill_ids.filtered(lambda bill: bill.type in ['in_invoice',
                                                                        'in_refund'] and bill.date_due and bill.date_due < fields.Date.today())
        overdue_amount = sum(bill.residual_signed for bill in overdue_bill_ids)
        return overdue_amount

    @api.depends('debit')
    def _debit_overdue_balance_get(self):
        for record in self:
            if not record.parent_id:
                total_overdue = self._get_amount_due_from_bill(record.invoice_ids)
                for child in record.child_ids:
                    total_overdue += self._get_amount_due_from_bill(child.invoice_ids)

                record.debit_overdue_amount = total_overdue
                record.debit_open_balance = record.debit - record.debit_overdue_amount
        return True

    # For Credit (Total Receivable)
    def _get_amount_due_from_invoice(self, invoice_ids):
        overdue_invoice_ids = invoice_ids.filtered(lambda invoice: invoice.type in ['out_invoice',
                                                                                    'out_refund'] and invoice.date_due and invoice.date_due < fields.Date.today())
        overdue_amount = sum(invoice.residual_signed for invoice in overdue_invoice_ids)
        return overdue_amount

    @api.depends('credit')
    def _overdue_balance_get(self):
        for record in self:
            if not record.parent_id:
                total_overdue = self._get_amount_due_from_invoice(record.invoice_ids)
                for child in record.child_ids:
                    total_overdue += self._get_amount_due_from_invoice(child.invoice_ids)

                record.overdue_amount = total_overdue
                record.open_balance = record.credit - record.overdue_amount
        return True

    @api.multi
    def write(self, vals):
        res = super(CustomerUSA, self).write(vals)
        for partner in self:
            for child in partner.child_ids:
                child.ar_in_charge = partner.ar_in_charge
        return res

    # Change Partner Ledger Label
    @api.depends('supplier', 'customer')
    def _compute_partner_ledger_label(self):
        for record in self:
            if record.supplier == record.customer:
                record.partner_ledger_label = _('Partner Balances')
            elif record.supplier:
                record.partner_ledger_label = _('Vendor Balances')
            else:
                record.partner_ledger_label = _('Customer Balances')

    # Change title of Partner Ledger report
    def open_partner_ledger(self):
        res = super(CustomerUSA, self).open_partner_ledger()
        if res.get('name', False):
            res['name'] = self.partner_ledger_label
        return res

    @api.multi
    def _num_open_invoices_get(self):
        if not self.ids:
            self.open_invoices = 0.0
            return True
        all_partners_and_children = {}
        all_partner_ids = []
        for partner in self:
            all_partners_and_children[partner] = self.with_context(active_test=False).search(
                [('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]

        invoices = self.env['account.invoice'].sudo().search(
            [('partner_id.id', 'in', all_partner_ids), ('state', '=', 'open'), ('type', '=', 'out_invoice')])
        temp_dict = {}
        for invoice in invoices:
            temp_dict[invoice.partner_id.id] = temp_dict.get(invoice.partner_id.id, 0) + 1
        for partner, child_ids in all_partners_and_children.items():
            partner.num_open_invoices = sum(temp_dict[key] for key in temp_dict if key in child_ids)

    @api.multi
    def action_view_open_invoices(self):
        self.ensure_one()
        action = self.env.ref('account.action_invoice_refund_out_tree').read()[0]
        action['domain'] = literal_eval(action['domain'])
        action['domain'].append(('partner_id', 'child_of', self.id))
        action['domain'].append(('state', '=', 'open'))
        action['domain'].append(('type', '=', 'out_invoice'))
        return action

    def _get_ref_next_sequence(self):
        return self.env[IR_SEQUENCE].next_by_code('customer.code')
