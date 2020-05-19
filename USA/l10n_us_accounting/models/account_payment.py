# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare
from odoo.tools.misc import formatLang
from ..utils.utils import has_multi_currency_group


class AccountPaymentUSA(models.Model):
    _inherit = 'account.payment'

    # set "required=False" and modify required condition in view
    journal_id = fields.Many2one(domain=[('type', 'in', ('bank', 'cash'))], string='Bank Account', required=False)
    ar_in_charge = fields.Many2one(string='AR In Charge', comodel_name='res.users')
    show_cancel_button = fields.Integer(string="Show cancel", compute='_show_cancel_button')

    # Add Open invoices to Payment
    open_invoice_ids = fields.One2many('usa.payment.invoice', 'payment_id')
    has_open_invoice = fields.Boolean(compute='_get_has_open_invoice', store=True)
    available_move_line_ids = fields.Many2many('account.move.line', compute='_get_available_move_line', store=True)
    payment_with_invoices = fields.Monetary('Payment with Invoices', compute='_get_total_payment', store=True)
    outstanding_payment = fields.Monetary('Outstanding Payment', compute='_get_outstanding_payment', store=True)

    # show transaction response when pay with credit card
    show_transaction_response = fields.Boolean(default=False, copy=False)

    check_number_text = fields.Char(compute='_compute_check_number_text', store=True)
    display_applied_invoices = fields.Boolean(compute='_get_display_applied_invoices',
                                              help="Technical field to display/hide applied invoices")

    # Keep Invoice/Bill Open or Write-off
    payment_writeoff_option = fields.Selection([
        ('open', 'Keep open'), ('reconcile', 'Mark invoice as fully paid')],
        default='open', string="Payment Write-off Option", copy=False)

    has_been_cashed = fields.Boolean('Has Been Cashed', compute='_compute_has_been_cashed',
                                     search='_search_has_been_cashed',
                                     help="True if this check payment has been matched with a bank statement line")

    @api.depends('check_number')
    def _compute_check_number_text(self):
        for record in self:
            if record.check_number:
                record.check_number_text = str(record.check_number)

    def close_transaction_response(self):
        self.show_transaction_response = False

    @api.depends('has_invoices', 'state', 'move_reconciled', 'payment_type')
    def _show_cancel_button(self):
        cancel_default = 0
        cancel_draft_and_unpaid = 1
        cancel_customer_payment_paid = 2
        cancel_vendor_payment_paid = 3
        cancel_reconciled_payment = 4

        for payment in self:
            is_posted_or_sent = payment.state in ('posted', 'sent')
            if payment.state == 'draft' or (is_posted_or_sent and not payment.has_invoices):
                payment.show_cancel_button = cancel_draft_and_unpaid
            elif all((is_posted_or_sent, payment.has_invoices, payment.payment_type == 'inbound')):
                payment.show_cancel_button = cancel_customer_payment_paid
            elif all((is_posted_or_sent, payment.has_invoices, payment.payment_type == 'outbound')):
                payment.show_cancel_button = cancel_vendor_payment_paid
            elif payment.state == 'reconciled':
                payment.show_cancel_button = cancel_reconciled_payment
            else:
                payment.show_cancel_button = cancel_default

    def get_bank_account(self):
        if self.payment_method_id and self.payment_type in ['inbound', 'outbound']:
            return {'domain': {'journal_id': ['&', ('type', 'in', ('bank', 'cash')), (
                self.payment_type + '_payment_method_ids.id', '=', self.payment_method_id.id)]}}
        return {'domain': {'journal_id': [('type', 'in', ('bank', 'cash'))]}}

    def _compute_journal_domain_and_types(self):
        res = super(AccountPaymentUSA, self)._compute_journal_domain_and_types()
        if self.currency_id.is_zero(self.amount):
            self.payment_difference_handling = 'open'
            if self.journal_id:
                return {'domain': [], 'journal_types': set([self.journal_id.type])}
            else:
                return {'domain': [], 'journal_types': set([])}
        return res

    @api.depends('open_invoice_ids', 'has_open_invoice', 'payment_type', 'partner_type')
    def _get_display_applied_invoices(self):
        for record in self:
            if (record.open_invoice_ids or record.has_open_invoice) and \
                    ((record.payment_type == 'inbound' and record.partner_type == 'customer') or
                         (record.payment_type == 'outbound' and record.partner_type == 'supplier')):
                record.display_applied_invoices = True
            else:
                record.display_applied_invoices = False

    def _compute_has_been_cashed(self):
        BSL = self.env['account.bank.statement.line']
        # check_printing is out_bound, batch_payment is in_bound
        check_payments = self.filtered(lambda x: x.payment_method_id.code in ['check_printing', 'batch_payment'] and
                                                 x.state not in ['draft', 'cancelled'])

        for record in check_payments:
            domain = [('status', '=', 'confirm')]
            if record.batch_payment_id:
                domain.append(('applied_batch_ids', 'in', [record.batch_payment_id.id]))
            else:
                domain.append(('applied_aml_ids', 'in', record.move_line_ids.ids))
            reviewed_transactions = BSL.search(domain)
            record.has_been_cashed = True if reviewed_transactions else False

    def _search_has_been_cashed(self, operator, value):
        BSL = self.env['account.bank.statement.line']
        reviewed_transactions = BSL.search([('status', '=', 'confirm')])

        results = self.search([('payment_method_id.code', 'in', ['check_printing', 'batch_payment']),
                               '|',
                               '&', ('batch_payment_id', '!=', False),
                               ('batch_payment_id.id', 'in', reviewed_transactions.mapped('applied_batch_ids').ids),
                               '&', ('batch_payment_id', '=', False),
                               ('move_line_ids', 'in', reviewed_transactions.mapped('applied_aml_ids').ids)])
        result_operator = 'not in'
        if (operator == "=" and value) or (operator == "!=" and not value):
            result_operator = 'in'
        return [('id', result_operator, results.ids)]

    # not return super()
    @api.onchange('amount', 'currency_id')
    def _onchange_amount(self):
        res = super(AccountPaymentUSA, self)._onchange_amount()
        return self.get_bank_account()

    @api.onchange('partner_id')
    def _onchange_select_customer(self):
        self.ar_in_charge = self.partner_id.ar_in_charge

    @api.multi
    def button_journal_entries(self):
        action = super(AccountPaymentUSA, self).button_journal_entries()
        action['name'] = _('Journal Entry')
        return action

    @api.multi
    def post(self):
        for payment in self:
            if payment.amount <= 0:
                raise ValidationError(_('Payment Amount must be greater than 0'))
        res = super(AccountPaymentUSA, self).post()

        # reconcile payment with open invoices
        for payment in self:
            # move_line is one of the aml of the current payment
            move_line = payment.move_line_ids.filtered(lambda line: line.account_id == payment.destination_account_id)

            if len(move_line) == 1:  # in case of internal transfer to the same account
                if move_line.reconciled is False:  # register payment in Invoice form
                    ctx = {}
                    for open_invoice in payment.open_invoice_ids.sorted(key=lambda r: r.id):
                        if not has_multi_currency_group(self):
                            ctx = {'partial_amount': open_invoice.payment}

                        if open_invoice.invoice_id:  # for invoice
                            invoice_id = open_invoice.invoice_id
                            invoice_id.with_context(ctx).assign_outstanding_credit(move_line.id)
                        else:  # for journal entry
                            mv_line_ids = [move_line.id, open_invoice.account_move_line_id.id]
                            self.env['account.reconciliation.widget'].with_context(ctx)\
                                .process_move_lines([{'mv_line_ids': mv_line_ids, 'type': 'account',
                                                      'id': payment.destination_account_id.id,
                                                      'new_mv_line_dicts': []}])
        return res

    def _create_write_off(self):
        inv_obj = self.env['account.invoice']
        invoices = inv_obj.browse(self.env.context.get('active_ids')).filtered(lambda x: x.state not in ['draft', 'cancel'])

        for payment in self:
            if payment.payment_writeoff_option == 'reconcile':

                for inv in invoices:
                    description = payment.writeoff_label
                    refund = inv.create_refund(payment.payment_difference, payment.currency_id, payment.writeoff_account_id,
                                               payment.payment_date, description, inv.journal_id.id)

                    # Put the reason in the chatter
                    subject = 'Write Off An Account'
                    body = description
                    refund.message_post(body=body, subject=subject)

                    # validate, reconcile and stay on invoice form.
                    to_reconcile_lines = inv.move_id.line_ids.filtered(lambda line:
                                                                       line.account_id.id == inv.account_id.id)
                    refund.action_invoice_open()  # validate write-off
                    to_reconcile_lines += refund.move_id.line_ids.filtered(lambda line:
                                                                           line.account_id.id == inv.account_id.id)
                    to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()

    def action_validate_invoice_payment(self):
        self._create_write_off()

        res = super(AccountPaymentUSA, self).action_validate_invoice_payment()

        for payment in self:
            invoice = payment.invoice_ids
            if invoice.ar_in_charge:
                payment.ar_in_charge = invoice.ar_in_charge
            elif invoice.partner_id.ar_in_charge:
                payment.ar_in_charge = invoice.partner_id.ar_in_charge

        return res

    @api.multi
    def delete_payment(self):
        self.unlink()
        return {'type': 'ir.actions.client', 'tag': 'history_back'}

    @api.multi
    def unlink(self):
        if any(record.state not in ('draft', 'cancelled') for record in self):
            raise UserError(
                'You cannot delete payment which is not draft or canceled. Please cancel this payment first.')
        for record in self:
            record.move_name = False
        return super(AccountPaymentUSA, self).unlink()

    # ADD OPEN INVOICES TO PAYMENT
    @api.depends('open_invoice_ids', 'open_invoice_ids.payment')
    def _get_total_payment(self):
        for record in self:
            payment_with_invoices = sum(inv.payment for inv in record.open_invoice_ids) \
                if record.open_invoice_ids else 0

            if record.state == 'draft' and record.outstanding_payment == 0:
                record.amount = payment_with_invoices

            record.payment_with_invoices = payment_with_invoices

    @api.depends('amount', 'payment_with_invoices')
    def _get_outstanding_payment(self):
        for record in self:
            record.outstanding_payment = record.amount - record.payment_with_invoices

    @api.depends('partner_id', 'currency_id')
    def _get_has_open_invoice(self):
        """
        To show or hide Open invoices section
        """
        for record in self:
            record.has_open_invoice = False

            if record.partner_id:
                domain = self._get_available_aml_domain(record)
                lines = self.env['account.move.line'].search(domain)
                if lines:
                    record.has_open_invoice = True

    @api.depends('partner_id', 'open_invoice_ids', 'state', 'currency_id')
    def _get_available_move_line(self):
        """
        Get available open invoices to add.
        """
        for record in self:
            if record.partner_id:
                added_ids = [line.account_move_line_id.id for line in record.open_invoice_ids]  # aml already added

                domain = [('id', 'not in', added_ids)]
                domain = self._get_available_aml_domain(record, domain)
                lines = self.env['account.move.line'].search(domain)
                record.available_move_line_ids = [(6, 0, lines.ids)]

    def _get_available_aml_domain(self, record, domain=None):
        domain = domain if domain else []
        domain.extend([('account_id', '=', record.destination_account_id.id),
                       ('reconciled', '=', False),
                       '|', ('partner_id', '=', self.env['res.partner']._find_accounting_partner(record.partner_id).id),
                       ('partner_id', '=', False),
                       '|', ('amount_residual', '!=', 0.0),
                       ('amount_residual_currency', '!=', 0.0)])

        # Find aml that have same currency with payment
        company_currency = record.company_id.currency_id if record.company_id else self.env.user.company_id.currency_id
        if not record.currency_id == company_currency:
            domain.extend([('currency_id', '=', record.currency_id.id)])
        else:
            domain.extend([('currency_id', '=', False)])

        if record.payment_type == 'inbound':  # customer payment
            domain.extend([('credit', '=', 0), ('debit', '>', 0)])
        elif record.payment_type == 'outbound':  # bill payment
            domain.extend([('credit', '>', 0), ('debit', '=', 0)])

        return domain

    @api.onchange('partner_id', 'currency_id')
    def _update_open_invoice_ids(self):
        self.open_invoice_ids = [(5,)]

    @api.multi
    def cancel(self):
        if all(payment_type == 'transfer' for payment_type in self.mapped('payment_type')):
            # For Internal Transfer, we need to unreconciled before we do cancel
            self.mapped('move_line_ids').remove_move_reconcile()

        res = super(AccountPaymentUSA, self).cancel()
        for record in self:
            # reset all values + remove from batch deposit
            record.write({'payment_with_invoices': 0, 'outstanding_payment': 0, 'amount': 0, 'batch_deposit_id': False})
            if record.open_invoice_ids:
                record.open_invoice_ids.unlink()
        return res

    # Check Printing
    def _check_make_stub_line(self, invoice):
        res = super()._check_make_stub_line(invoice)

        # Get Credit/Discount Amount
        credit_amount = 0
        amount_field = 'amount_currency' if self.currency_id != self.journal_id.company_id.currency_id else 'amount'
        # Looking for Vendor Credit Note in Vendor Bill
        if invoice.type in ['in_invoice', 'out_refund']:
            # This is for Vendor Bill only
            credit_note_ids = invoice.move_id.line_ids.mapped('matched_debit_ids').filtered(
                lambda r: r.debit_move_id.invoice_id and r.debit_move_id.invoice_id.type == 'in_refund')
            credit_amount = abs(sum(credit_note_ids.mapped(amount_field)))

            # Calculate Other Payment amount
            other_payment_ids = invoice.move_id.line_ids.mapped('matched_debit_ids').filtered(
                lambda r: r.debit_move_id not in self.move_line_ids and r.id not in credit_note_ids.ids)
            other_payment_amount = abs(sum(other_payment_ids.mapped(amount_field)))

        # Update Amount Residual, BEFORE apply this check
        amount_residual = invoice.amount_total - other_payment_amount

        res.update({'credit_amount': formatLang(self.env, credit_amount, currency_obj=invoice.currency_id),
                    'amount_residual': formatLang(self.env, amount_residual,
                                                  currency_obj=invoice.currency_id) if amount_residual * 10 ** 4 != 0 else '-'
                    })

        return res

    def _check_build_page_info(self, i, p):
        res = super()._check_build_page_info(i, p)

        if self.partner_id.print_check_as:
            res['partner_name'] = self.partner_id.check_name

        return res

    ####################################################
    # CRUD methods
    ####################################################
    @api.model
    def create(self, values):
        payment = super(AccountPaymentUSA, self).create(values)
        if not payment.ar_in_charge and payment.partner_id.ar_in_charge:
            payment.ar_in_charge = payment.partner_id.ar_in_charge

        # If payment is created from a voucher, link them.
        if values.get('voucher_id', False):
            voucher = self.env['account.voucher'].browse(values['voucher_id'])
            voucher.payment_id = payment.id
        return payment

    @api.multi
    def write(self, vals):
        if 'show_transaction_response' not in vals:
            vals['show_transaction_response'] = False

        res = super(AccountPaymentUSA, self).write(vals)

        for record in self:
            if float_compare(record.amount, record.payment_with_invoices, precision_digits=2) < 0:
                if record.payment_type == 'inbound':
                    raise ValidationError(_('Invalid payment amount.\n'
                                            'Payment amount should be equal or greater than '
                                            'payment amount for all open invoices.'))
                elif record.payment_type == 'outbound':
                    raise ValidationError(_('Invalid payment amount.\n'
                                            'Payment amount should be equal or greater than '
                                            'payment amount for all open bills.'))
        return res

    @api.model_cr_context
    def _init_column(self, column_name):
        if column_name not in ('has_open_invoice'):
            super(AccountPaymentUSA, self)._init_column(column_name)
        elif column_name == 'has_open_invoice':
            posted_payments = self.sudo().search([('state', 'not in', ['draft', 'cancelled']),
                                                  ('payment_type', '!=', 'transfer')])

            query = """INSERT INTO usa_payment_invoice (payment_id, account_move_line_id, payment)
                      VALUES (%(payment_id)s, %(move_line_id)s, %(payment_amount)s)"""
            query_list = []
            for payment in posted_payments:
                receivable_lines = payment.move_line_ids.filtered(lambda x: x.account_id.internal_type == 'receivable')
                payable_lines = payment.move_line_ids.filtered(lambda x: x.account_id.internal_type == 'payable')

                if receivable_lines:
                    matched_debit_ids = receivable_lines.mapped('matched_debit_ids')
                    query_list.extend([{'payment_id': payment.id, 'move_line_id': debit.debit_move_id.id,
                                        'payment_amount': debit.amount}
                                       for debit in matched_debit_ids])
                if payable_lines:
                    matched_credit_ids = payable_lines.mapped('matched_credit_ids')
                    query_list.extend([{'payment_id': payment.id, 'move_line_id': credit.credit_move_id.id,
                                        'payment_amount': credit.amount}
                                       for credit in matched_credit_ids])
            if query_list:
                self.env.cr._obj.executemany(query, query_list)
                self.env.cr.commit()
