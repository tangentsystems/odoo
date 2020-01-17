# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

import json
import locale
import operator as py_operator
from collections import deque
from datetime import date
from itertools import zip_longest

from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


OPERATORS = {'<': py_operator.lt, '>': py_operator.gt, '<=': py_operator.le, '>=': py_operator.ge, '=': py_operator.eq,
             '!=': py_operator.ne}

PERCENT_TERM = 'percent'
FIXED_TERM = 'fixed'
BALANCE_TERM = 'balance'


class AccountInvoiceUSA(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def create(self, values):
        field_name = 'is_write_off'
        values[field_name] = self.env.context.get(field_name, False)
        invoice = super(AccountInvoiceUSA, self).create(values)
        if not invoice.ar_in_charge and invoice.partner_id.ar_in_charge:
            invoice.ar_in_charge = invoice.partner_id.ar_in_charge
        return invoice

    @api.onchange('partner_id')
    def _onchange_select_customer(self):
        self.ar_in_charge = self.partner_id.ar_in_charge

    @api.one
    def _get_outstanding_info_JSON(self):
        super(AccountInvoiceUSA, self)._get_outstanding_info_JSON()
        try:
            outstanding_credits_debits = json.loads(self.outstanding_credits_debits_widget)
            content = outstanding_credits_debits['content']
            content_dict = {line['id']: line for line in content}

            for line in self.env['account.move.line'].browse(content_dict.keys()):
                content_dict[line['id']].update({
                    'invoice_id': line.invoice_id.id,
                    'payment_id': line.payment_id.id,
                    'move_id': line.move_id.id,
                    'journal_name': line.move_id.name or line.ref,
                })
            outstanding_credits_debits['type'] = self.type

            self.outstanding_credits_debits_widget = json.dumps(outstanding_credits_debits)
        except Exception as _:
            pass
        return True

    @api.model
    def _get_payments_vals(self):
        payment_vals = super(AccountInvoiceUSA, self)._get_payments_vals()

        # bulid dict of invoices
        invoices = {payment.invoice_id.id: payment.invoice_id for payment in self.payment_move_line_ids}

        invoice_type = self.type
        for payment_val in payment_vals:
            payment_val.update({
                'type': invoice_type,
                'is_write_off': invoices[payment_val['invoice_id']].is_write_off,
            })
        return payment_vals

    def _get_seq_number_next_stuff(self):
        self.ensure_one()
        journal_sequence, domain = super(AccountInvoiceUSA, self)._get_seq_number_next_stuff()
        if self.env.context.get('is_write_off'):
            journal_sequence = self.journal_id.write_off_sequence_id

        return journal_sequence, domain

    ar_in_charge = fields.Many2one(string='AR In Charge', comodel_name='res.users')

    aging_days = fields.Integer(string='Aging Days', compute='_compute_aging_days', search='_search_aging_days',
                                store=True)

    fiscal_quarter = fields.Char(string='Fiscal Quarter', compute='_compute_fiscal_quarter',
                                 search='_search_fiscal_quarter')

    last_fiscal_quarter = fields.Char(string='Last Fiscal Quarter', compute='_compute_last_fiscal_quarter',
                                      search='_search_last_fiscal_quarter')

    fiscal_year = fields.Date(string='Fiscal Year', compute='_compute_fiscal_year', search='_search_fiscal_year')

    last_fiscal_year = fields.Date(string='Last Fiscal Year', compute='_compute_last_fiscal_year',
                                   search='_search_last_fiscal_year')

    internal_notes = fields.Text(string='Internal Notes')

    is_write_off = fields.Boolean(string='Is Write Off', default=False)

    def _compute_fiscal_quarter(self):
        for record in self:
            record.fiscal_quarter = None

    def _compute_last_fiscal_quarter(self):
        for record in self:
            record.last_fiscal_quarter = None

    def _compute_fiscal_year(self):
        for record in self:
            record.fiscal_year = None

    def _compute_last_fiscal_year(self):
        for record in self:
            record.last_fiscal_year = None

    def _search_fiscal_year(self, operator, value):
        fiscal_year_date = self._get_fiscal_year_date()

        return ['&', ('date_invoice', '>=', str(fiscal_year_date + relativedelta.relativedelta(years=-1, days=1))),
                ('date_invoice', '<=', str(fiscal_year_date))]

    def _get_fiscal_year_date(self):
        company_id = self.env.user.company_id
        last_day = str(company_id.fiscalyear_last_day)
        last_month = str(company_id.fiscalyear_last_month)
        return fields.Date.from_string('-'.join((str(date.today().year), last_month, last_day)))

    def _search_fiscal_quarter(self, operator, value):
        start_quarter = self._calculate_start_quarter()
        end_quarter = start_quarter + relativedelta.relativedelta(months=3, days=-1)

        return ['&', ('date_invoice', '>=', str(start_quarter)), ('date_invoice', '<=', str(end_quarter))]

    def _calculate_start_quarter(self):
        fiscal_year_date = self._get_fiscal_year_date()

        months = deque(range(1, 13))
        months.rotate(12 - fiscal_year_date.month)
        new_months = list(months)

        current_month = date.today().month

        quarter = None
        is_decrease_year = False
        index = 0
        for month_group in zip_longest(*[iter(new_months)] * 3):
            for month in month_group:
                if current_month == month:
                    quarter = index // 3 + 1
                    if month_group[0] > month_group[-1] and current_month == month_group[-1]:
                        is_decrease_year = True
                    break
                index += 1
            if quarter:
                break

        start_month = str(new_months[::3][quarter - 1])
        start_year = str(fiscal_year_date.year - 1) if is_decrease_year else str(fiscal_year_date.year)
        return fields.Date.from_string('-'.join((start_year, start_month, '1')))

    def _search_last_fiscal_quarter(self, operator, value):
        start_quarter = self._calculate_start_quarter()
        last_quarter_start = start_quarter + relativedelta.relativedelta(months=-3)
        last_quarter_end = start_quarter + relativedelta.relativedelta(days=-1)

        return ['&', ('date_invoice', '>=', str(last_quarter_start)), ('date_invoice', '<=', str(last_quarter_end))]

    def _search_last_fiscal_year(self, operator, value):
        fiscal_year_date = self._get_fiscal_year_date()
        last_year_start = fiscal_year_date + relativedelta.relativedelta(years=-2, days=1)
        last_year_end = fiscal_year_date + relativedelta.relativedelta(years=-1)

        return ['&', ('date_invoice', '>=', str(last_year_start)), ('date_invoice', '<=', str(last_year_end))]

    def _parse_payment_term(self, pterm_list):
        sum_amount = 0
        payment_term_list = []
        for index, item in enumerate(self.payment_term_id.line_ids):
            if len(pterm_list) > index and len(pterm_list[index]) > 0:
                term = {'due_date': pterm_list[index][0]}

                if item.value == PERCENT_TERM:
                    term['pay_amount'] = self.amount_total * item.value_amount / 100
                    sum_amount += term['pay_amount']
                elif item.value == FIXED_TERM:
                    term['pay_amount'] = item.value_amount
                    sum_amount += term['pay_amount']
                elif item.value == BALANCE_TERM:
                    term['pay_amount'] = self.amount_total - sum_amount

                payment_term_list.append(term)

        return payment_term_list

    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        date_invoice = self.date_invoice

        if self.payment_term_id:
            pterm = self.payment_term_id.with_context(currency_id=self.company_id.currency_id.id)
            pterm_list = self._parse_payment_term(pterm.compute(value=1, date_ref=date_invoice)[0])

            amount_payed = self.amount_total - self.residual
            if amount_payed > 0:
                for line in pterm_list:
                    amount_payed -= line['pay_amount']
                    if amount_payed <= 0:
                        self.date_due = line['due_date']
                        break
            else:
                self.date_due = min(line['due_date'] for line in pterm_list)
        elif self.date_due and date_invoice and date_invoice > self.date_due:
            self.date_due = date_invoice

    @api.depends('date_due', 'state')
    def _compute_aging_days(self):
        today = fields.Date.from_string(fields.Date.today())
        for record in self:
            if record.state != 'open':
                record.aging_days = 0
            else:
                if record.date_due:
                    timedelta = today - fields.Date.from_string(record.date_due)
                    record.aging_days = timedelta.days
                    if record.aging_days < 0:
                        record.aging_days = 0
                else:
                    record.aging_days = 0

    @api.model
    def _search_aging_days(self, operator, value):
        ids = [invoice.id for invoice in self.search([]) if OPERATORS[operator](invoice.aging_days, value)]
        return [('id', 'in', ids)]

    @api.model
    def _cron_aging_days(self):
        today = fields.Date.from_string(fields.Date.today())
        invoices = self.search([('state', '=', 'open')])
        for record in invoices:
            if record.date_due:
                timedelta = today - fields.Date.from_string(record.date_due)
                record.aging_days = timedelta.days
                if record.aging_days < 0:
                    record.aging_days = 0
            else:
                record.aging_days = 0

    @api.multi
    def create_refund(self, write_off_amount, company_currency_id, account_id, date_invoice=None, description=None,
                      journal_id=None):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(invoice, date_invoice=date_invoice, date=False, description=description,
                                          journal_id=journal_id)

            # Update value from Write Off An Account form
            values.update(
                self._build_invoice_line_item(abs(write_off_amount), company_currency_id.id, account_id.id,
                                              values['invoice_line_ids']))
            # Update is_write_off flag
            values['is_write_off'] = True
            values['fiscal_position_id'] = False

            refund_invoice = self.create(values)

            # Update name of invoice line to Write Off
            refund_invoice['invoice_line_ids'][0].update({
                'name': 'Write Off',
                'display_name': 'Write Off',
            })

            # Create message post
            message = 'This write off was created from ' \
                      '<a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>' % (invoice.id, invoice.number)
            refund_invoice.message_post(body=message)

            new_invoices += refund_invoice
        return new_invoices

    @staticmethod
    def _build_invoice_line_item(write_off_amount, company_currency_id, account_id, invoice_line_ids):
        if invoice_line_ids:
            first_value, second_value, write_off_bad_debt = invoice_line_ids[0]
            first_line_tax, second_line_tax, _ = write_off_bad_debt['invoice_line_tax_ids'][0]
            write_off_bad_debt.update(
                name='Write Off',
                display_name='Write Off',
                uom_id=False,
                currency_id=company_currency_id,
                company_currency_id=company_currency_id,
                account_id=account_id,
                quantity=1.0,
                price_unit=write_off_amount,
                product_id=False,
                invoice_line_tax_ids=[(first_line_tax, second_line_tax, [])],
                discount=0.0,
                product_image=False
            )
            new_invoice_line_ids = [(first_value, second_value, write_off_bad_debt)]
        else:
            new_invoice_line_ids = [(0, 0, [])]

        return {'invoice_line_ids': new_invoice_line_ids, 'tax_line_ids': []}

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        for index, item in reversed(list(enumerate(domain or []))):
            if 'amount_total_signed' in item:
                amount = item[2]
                locale.setlocale(locale.LC_ALL, '%s.UTF-8' % self.env.lang)
                try:
                    item[2] = locale.atof(amount.replace(self.env.user.company_id.currency_id.symbol, ''))
                except ValueError:
                    # Remove data and operator
                    del domain[index]
                    domain.remove('|')
                break
        return super(AccountInvoiceUSA, self).search_read(domain, fields, offset, limit, order)

    @api.multi
    def action_cancel(self):
        for inv in self:
            if inv.payment_move_line_ids:
                if inv.type in ('out_invoice', 'in_invoice'):
                    raise UserError(_(
                        'You cannot cancel a transaction which is partially paid. Please remove related payment entries first.'))
                elif inv.type in ('out_refund'):
                    raise UserError(_(
                        'You cannot cancel a transaction which is partially allocated. Please remove related invoice(s) first.'))
                elif inv.type in ('in_refund'):
                    raise UserError(_(
                        'You cannot cancel a transaction which is partially allocated. Please remove related bill(s) first.'))
        # First, set the invoices as cancelled and detach the move ids
        return super(AccountInvoiceUSA,self).action_cancel()

    @api.multi
    def action_invoice_cancel(self):
        for inv in self.filtered(lambda i: i.state in ['paid'] and i.payment_move_line_ids):
            if inv.type in ('out_invoice', 'in_invoice'):
                raise UserError(
                    _("You cannot cancel a transaction which is paid. Please remove related payment entries first."))
            elif inv.type in ('out_refund'):
                raise UserError(
                    _("You cannot cancel a transaction which is allocated. Please remove related invoice(s) first."))
            elif inv.type in ('in_refund'):
                raise UserError(
                    _("You cannot cancel a transaction which is allocated. Please remove related bill(s) first."))
        return super(AccountInvoiceUSA, self).action_invoice_cancel()

    def action_delete(self):
        if self.state not in ['draft', 'cancel']:
            raise UserError(_(
                    'You cannot delete transaction which is not draft or canceled. Please cancel this transaction first.'))
        self.move_name = False
        super(AccountInvoiceUSA, self).unlink()
        return {'type': 'ir.actions.client', 'tag': 'history_back'}

    @api.multi
    def open_form(self):
        self.ensure_one()
        action = False
        if self.is_write_off:
            action = self.env.ref('l10n_us_accounting.action_invoice_write_off_usa').read()[0]
            action['views'] = [(self.env.ref('l10n_us_accounting.write_off_form_usa').id, 'form')]
        else:
            if self.type == 'out_refund':
                action = self.env.ref('account.action_invoice_out_refund').read()[0]
                action['views'] = [(self.env.ref('l10n_us_accounting.credit_note_form_usa').id, 'form')]
            elif self.type == 'in_refund':
                action = self.env.ref('account.action_invoice_in_refund').read()[0]
                action['views'] = [(self.env.ref('l10n_us_accounting.credit_note_supplier_form_usa').id, 'form')]
            elif self.type == 'out_invoice':
                action = self.env.ref('account.action_invoice_tree1').read()[0]
                action['views'] = [(self.env.ref('l10n_us_accounting.invoice_form_usa').id, 'form')]
            elif self.type == 'in_invoice':
                action = self.env.ref('account.action_invoice_tree2').read()[0]
                action['views'] = [(self.env.ref('l10n_us_accounting.invoice_supplier_form_usa').id, 'form')]
        return action

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': 'Invoice',
            'in_invoice': 'Vendor Bill',
            'out_refund': 'Credit Note',
            'in_refund': 'Vendor Credit note',
            'write_off': 'Write-off',
        }
        result = []
        append_result = result.append
        for inv in self:
            type = 'write_off' if inv.is_write_off else inv.type
            append_result((inv.id, '%s %s' % (inv.number or TYPES[type], inv.name or '')))
        return result

    def _get_printed_report_name(self):
        self.ensure_one()

        if self.type == 'out_refund' and self.is_write_off:
            return self.state == 'draft' and _('Writeoff') or \
                   self.state in ('open', 'paid') and _('Writeoff - %s') % (self.number)
        else:
            return super(AccountInvoiceUSA, self)._get_printed_report_name()
