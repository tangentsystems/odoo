# -*- coding: utf-8 -*-
import itertools
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_utils

from ..models.model_const import (
    ACCOUNT_BATCH_DEPOSIT,
    ACCOUNT_MOVE_LINE,
    ACCOUNT_MATCHING_BANK_STATEMENT_LINE,
    ACCOUNT_BANK_STATEMENT_LINE_MAPPING,
    ACCOUNT_JOURNAL,
    ACCOUNT_VOUCHER,
    ACCOUNT_PAYMENT
)


class AccountBankStatementLineUSA(models.Model):
    _name = 'account.bank.statement.line'
    _inherit = ['account.bank.statement.line', 'account.caching.mixin.usa', 'mail.thread', 'mail.activity.mixin']

    # Rename
    name = fields.Char(string='Description')
    account_id = fields.Many2one(string='Account')

    # Modify
    journal_entry_ids = fields.One2many(ondelete='set null')

    # New fields
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null')
    amount_unsigned = fields.Monetary(string='Amount', digits=0, currency_field='journal_currency_id', readonly=True,
                                      compute='_compute_amount_unsigned', store=True)

    mapping_transaction_ids = fields.One2many('account.bank.statement.line.mapping', 'mapping_id',
                                              string='Mapping Transaction', copy=False, readonly=True)
    candidate_transactions_ids = fields.One2many('account.matching.bank.statement.line', 'mapping_id',
                                                 string='Candidate Transactions', copy=False)

    possible_match = fields.Char(string='Possible Match', compute='_compute_possible_match')

    transaction_type = fields.Selection([
        ('amount_paid', 'Send Money'),
        ('amount_received', 'Receive Money')
    ], string='Transaction Type', compute='_compute_transaction_type', store=True, readonly=True)

    sent = fields.Monetary(string='Sent', digits=0, currency_field='journal_currency_id',
                           compute='_compute_sent_or_received', store=True)
    received = fields.Monetary(string='Received', digits=0, currency_field='journal_currency_id',
                               compute='_compute_sent_or_received', store=True)
    status = fields.Selection([('open', 'New'), ('confirm', 'Validated'), ('ignore', 'Exclude')], string='Review Status',
                              required=True, readonly=False, copy=False, default='open', track_visibility='onchange')
    action_type = fields.Selection([('add', 'Add'), ('match', 'Match'), ('transfer', 'Transfer')], string='Action Type',
                                   required=True, copy=False, default='add')

    bank_rule_apply = fields.Many2one('account.reconcile.model', string='Rule Applied', readonly=True,
                                      ondelete='set null', copy=False,
                                      help='Show the bank rule that is applied to this bank statement')
    memo = fields.Char(string='Memo', default=lambda self: self._context.get('name'))

    payment = fields.Monetary(string='Selected Transaction(s)', compute='_compute_payment',
                              currency_field='journal_currency_id', readonly=True, store=True, copy=False)
    difference = fields.Monetary(string='Difference', compute='_compute_difference',
                                 currency_field='journal_currency_id', readonly=True, store=True, copy=False,
                                 help='Calculate difference between selected transaction and downloaded transaction')

    show_add_transaction = fields.Boolean(compute='_compute_show_add_transaction')

    add_transaction = fields.Boolean(string='Add new transaction', default=False)
    new_date = fields.Date(copy=False, help='The date is shown in add new transaction')
    new_account_id = fields.Many2one('account.account', string='Account', ondelete='cascade',
                                     domain=[('deprecated', '=', False)])
    new_partner_id = fields.Many2one('res.partner', string='Payee', ondelete='set null')
    new_memo = fields.Char(string='Memo')
    new_amount = fields.Monetary(string='Amount', compute='_compute_new_amount', store=True, readonly=True,
                                 currency_field='journal_currency_id')

    add_transaction_input = fields.Boolean(string='Add new transaction', default=False)
    new_date_input = fields.Date(copy=False, help='The date is input in add new transaction')
    new_account_id_input = fields.Many2one('account.account', string='Account', ondelete='cascade',
                                           domain=[('deprecated', '=', False)])
    new_partner_id_input = fields.Many2one('res.partner', string='Payee', ondelete='set null')
    new_memo_input = fields.Char(string='Memo')
    new_amount_input = fields.Monetary(string='Amount', compute='_compute_new_amount_input', store=True, readonly=True,
                                       currency_field='journal_currency_id')

    split_transaction = fields.Boolean(string='Split', default=False)

    line_ids = fields.One2many('account.bank.statement.line.split.account', 'line_id')
    total_split_amount = fields.Monetary(string='Split Amount', compute='_compute_total_split_amount', store=True,
                                         readonly=True, currency_field='journal_currency_id')
    bank_rule_apply_tracking = fields.Char(string='Bank Rule Apply Tracking')

    selected_transactions_amount = fields.Monetary(string='Selected Transaction(s)',
                                                   compute='_compute_selected_transactions_amount',
                                                   readonly=True, copy=False, currency_field='journal_currency_id')
    difference_other_matching = fields.Monetary(string='Difference', compute='_compute_difference_other_matching',
                                                currency_field='journal_currency_id', readonly=True, copy=False,
                                                help='Calculate difference between selected transaction, '
                                                     'new Transaction and downloaded transaction')

    # linked transaction
    applied_aml_ids = fields.Many2many('account.move.line', 'applied_aml_bsl_table',
                                       compute='_compute_applied_transaction', store=True)
    applied_batch_ids = fields.Many2many('account.batch.payment', 'applied_batch_bsl_table',
                                         compute='_compute_applied_transaction', store=True)
    added_or_matched_description = fields.Char(compute='_compute_add_match_description', store=True)
    account_voucher_id = fields.Many2one('account.voucher')
    account_voucher_purchase_id = fields.Many2one('account.voucher', related='account_voucher_id')
    account_payment_id = fields.Many2one('account.payment')
    journal_entries_count = fields.Integer(compute='_count_journal_entries', string='Journal Items')

    account_id_transfer = fields.Many2one('account.journal', string='Account', ondelete='set null', domain=[('type', '=', 'bank')])

    @api.multi
    @api.depends('amount')
    def _compute_amount_unsigned(self):
        for record in self:
            record.amount_unsigned = abs(record.amount)

    @api.multi
    @api.depends('amount')
    def _compute_sent_or_received(self):
        for record in self:
            if record.amount < 0:
                record.sent = abs(record.amount)
                record.received = None
            else:
                record.sent = None
                record.received = record.amount

    @api.multi
    @api.depends('amount')
    def _compute_transaction_type(self):
        for record in self:
            record.transaction_type = 'amount_paid' if record.amount < 0 else 'amount_received'

    @api.multi
    @api.depends('mapping_transaction_ids')
    def _compute_possible_match(self):
        for record in self:
            record.possible_match = record.mapping_transaction_ids and record.mapping_transaction_ids[0].name or ''

    @api.multi
    @api.depends('amount_unsigned', 'payment', 'total_split_amount',
                 'add_transaction', 'split_transaction', 'action_type',
                 'new_amount')
    def _compute_difference(self):
        for record in self:
            if record.action_type == 'add' and record.split_transaction:
                record.difference = record.amount_unsigned - record.total_split_amount
            elif record.action_type == 'match':
                if record.add_transaction:
                    record.difference = record.amount_unsigned - record.new_amount - record.payment
                else:
                    record.difference = record.amount_unsigned - record.payment

    @api.multi
    @api.depends('mapping_transaction_ids')
    def _compute_payment(self):
        for record in self:
            record.payment = sum(transaction.total_amount for transaction in record.mapping_transaction_ids or [])

    @api.multi
    @api.depends('action_type', 'add_transaction', 'payment')
    def _compute_new_amount(self):
        for record in self:
            if record.action_type == 'match' and record.add_transaction:
                record.new_amount = record.amount_unsigned - record.payment
            else:
                record.new_amount = 0.0

    @api.multi
    @api.depends('action_type', 'add_transaction_input', 'payment')
    def _compute_new_amount_input(self):
        for record in self:
            if record.action_type == 'match' and record.add_transaction_input:
                record.new_amount_input = record.amount_unsigned - record.payment
            else:
                record.new_amount_input = 0.0

    @api.multi
    @api.depends('line_ids.amount', 'split_transaction')
    def _compute_total_split_amount(self):
        for record in self:
            record.total_split_amount = sum(line_id.amount for line_id in record.line_ids or []) if record.split_transaction \
                else 0.0

    @api.multi
    @api.depends('action_type', 'selected_transactions_amount')
    def _compute_show_add_transaction(self):
        for record in self:
            record.show_add_transaction = float_utils.float_compare(record.amount_unsigned,
                                                                    record.selected_transactions_amount, 2) != 0

    @api.multi
    @api.depends('candidate_transactions_ids.selected_item')
    def _compute_selected_transactions_amount(self):
        for record in self:
            if record.action_type == 'match':
                record.selected_transactions_amount = sum(
                    candidate_transaction.total_amount for candidate_transaction in record.candidate_transactions_ids if
                    candidate_transaction.selected_item
                )

    @api.multi
    @api.depends('selected_transactions_amount', 'new_amount_input')
    def _compute_difference_other_matching(self):
        for record in self:
            record.difference_other_matching = record.amount_unsigned - record.selected_transactions_amount - record.new_amount_input

    @api.depends('status')
    def _compute_applied_transaction(self):
        for record in self:
            account_ids = [record.journal_id.default_debit_account_id.id,
                           record.journal_id.default_credit_account_id.id]

            applied_batch_ids = []
            applied_aml_ids = []
            if record.mapping_transaction_ids:
                applied_batch_ids = [(4, x.mapped('batch_deposit_id').id) for x in
                                     record.mapping_transaction_ids.filtered(lambda line: line.batch_deposit_id)]
                applied_aml_ids = [(4, x.mapped('journal_entry_id').id) for x in
                                   record.mapping_transaction_ids.filtered(lambda line: line.journal_entry_id)]
            if record.account_voucher_id and record.account_voucher_id.move_id:
                payment_id = record.account_voucher_id.payment_id
                aml_ids = payment_id.move_line_ids.filtered(lambda x: x.account_id.id in account_ids)
                applied_aml_ids.extend([(4, x.id) for x in aml_ids])
            if record.account_payment_id and record.account_payment_id.move_line_ids:
                aml_ids = record.account_payment_id.move_line_ids.filtered(lambda x: x.account_id.id in account_ids)
                applied_aml_ids.extend([(4, x.id) for x in aml_ids])

            if applied_aml_ids:
                record.applied_aml_ids = applied_aml_ids
            if applied_batch_ids:
                record.applied_batch_ids = applied_batch_ids

    @api.onchange('selected_transactions_amount')
    def _onchange_show_add_transaction(self):
        if float_utils.float_compare(self.amount_unsigned, self.selected_transactions_amount, 2) != 0:
            self.show_add_transaction = True
        else:
            self.update({
                'show_add_transaction': None,
                'add_transaction_input': None,
                'new_date_input': None,
                'new_partner_id_input': None,
                'new_account_id_input': None,
                'new_memo_input': None,
                'new_amount_input': 0.0
            })

    @api.onchange('add_transaction_input', 'selected_transactions_amount')
    def _onchange_new_amount_input(self):
        if self.add_transaction_input and \
                        float_utils.float_compare(self.amount_unsigned, self.selected_transactions_amount, 2) != 0:
            self.new_amount_input = self.amount_unsigned - self.selected_transactions_amount
        else:
            self.new_amount_input = 0.0
            self.update({
                'add_transaction_input': None,
                'new_date_input': None,
                'new_partner_id_input': None,
                'new_account_id_input': None,
                'new_memo_input': None,
                'new_amount_input': 0.0
            })

    @api.multi
    @api.onchange('action_type')
    def _onchange_reset_all_value_difference_action_type(self):
        for record in self:
            if record.action_type == 'add':  # Reset all values that are difference Add
                record.update({
                    'mapping_transaction_ids': None,
                    'candidate_transactions_ids': None,
                    'account_id_transfer': None,
                    'account_id': None,
                    'show_add_transaction': None,
                    'add_transaction': None,
                    'new_date': None,
                    'new_partner_id': None,
                    'new_account_id': None,
                    'new_memo': None,
                })
            elif record.action_type == 'match':  # Reset all values that are difference Match
                record.update({
                    'account_id': None,
                    'analytic_account_id': None,
                    'account_id_transfer': None,
                    'partner_id': None,
                    'split_transaction': False,
                    'line_ids': None,
                })
            else:  # transfer
                record.update({
                    'mapping_transaction_ids': None,
                    'candidate_transactions_ids': None,
                    'account_id': None,
                    'analytic_account_id': None,
                    'partner_id': None,
                    'split_transaction': False,
                    'add_transaction': False,
                    'line_ids': None,
                    'new_date': None,
                    'new_partner_id': None,
                    'new_account_id': None,
                    'new_memo': None,
                })

    @api.multi
    @api.onchange('split_transaction')
    def _onchange_line_ids(self):
        for record in self:
            if not record.split_transaction:
                record.update({
                    'line_ids': None,
                    'account_id': None,
                    'analytic_account_id': None
                })

    @api.multi
    @api.onchange('account_id_transfer')
    def _onchange_journal_transfer(self):
        """
        Update account of bsl from Journal's account
        For displaying purpose only
        """
        for record in self:
            if record.action_type == 'transfer' and record.account_id_transfer:
                if record.transaction_type == 'amount_paid':
                    record.account_id = record.account_id_transfer.default_credit_account_id
                else:  # receive
                    record.account_id = record.account_id_transfer.default_debit_account_id

    @api.onchange('candidate_transactions_ids')
    def _onchange_selected_transactions_amount(self):
        self.selected_transactions_amount = sum(
            candidate_transaction.total_amount for candidate_transaction in self.candidate_transactions_ids if
            candidate_transaction.selected_item
        )

    @api.multi
    @api.constrains('difference_other_matching')
    def _check_difference_other_matching(self):
        for record in self:
            if record.difference_other_matching != 0:
                raise ValidationError('The selected and downloaded transaction amounts don\'t match. '
                                      'To continue, please resolve the difference.')

    @api.multi
    @api.constrains('new_amount')
    def _check_new_amount(self):
        for record in self:
            if record.new_amount < 0:
                raise ValidationError('Amount of new transaction must be greater than 0')

    @api.multi
    @api.constrains('new_amount_input')
    def _check_new_amount_input(self):
        for record in self:
            if record.new_amount_input < 0:
                raise ValidationError('Amount of new transaction must be greater than 0')

    @api.multi
    def _validate_difference(self, bypass_validation=False):
        if bypass_validation:
            return

        for record in self:
            if record.difference != 0:
                if record.action_type == 'match':
                    raise ValidationError('The downloaded and selected transaction amounts don\'t match. '
                                          'To continue, please resolve the difference.')
                elif record.action_type == 'add' and record.split_transaction:
                    raise ValidationError('Split line amounts must add up exactly to the original amount')

    @api.multi
    @api.depends('account_voucher_id', 'account_payment_id', 'status')
    def _compute_add_match_description(self):
        for record in self:
            if record.status == 'confirm':
                if record.action_type in ('add', 'transfer'):
                    if record.account_voucher_id:
                        record.added_or_matched_description = 'Added to ' + record.account_voucher_id.number
                    elif record.account_payment_id:
                        record.added_or_matched_description = 'Added to ' + record.account_payment_id.name
                else:  # match case
                    size_of_mapping = len(record.mapping_transaction_ids)
                    if size_of_mapping > 1 or (size_of_mapping == 1 and record.add_transaction):
                        record.added_or_matched_description = 'Matched to multiple transactions'
                    elif size_of_mapping == 1:
                        record.added_or_matched_description = 'Matched to %s' % record.possible_match
                    elif record.add_transaction and record.account_voucher_id:
                        record.added_or_matched_description = 'Matched to %s' % record.account_voucher_id.number

    def _get_log_msg(self, transaction, is_transfer):
        transaction_type = 'Transfer' if is_transfer else 'Receipt'
        msg = False

        if transaction:
            transaction_name = transaction.name if is_transfer else transaction.number
            msg_link = '<a href=javascript:void(0) data-oe-model={} data-oe-id={}>{}</a>'. \
                format(transaction._name, transaction.id, transaction_name)
            msg = 'A new {} has been created: {}'.format(transaction_type, msg_link)
        # TODO: check if it's a receipt or transfer from Undo function???
        # else:
        #     msg = "{} has been removed successfully.".format(transaction_type)

        return msg

    def _log_message_statement(self, vals, is_transfer=False):
        """
        Log message when a new Receipt/Transfer is created/deleted
        :param vals: vals of write function.
        :param is_transfer: True if it's a Transfer, otherwise Receipt
        """
        for record in self:
            if is_transfer:
                transfer_id = vals.get('account_payment_id', False)
                transaction = self.env['account.payment'].browse(transfer_id) if transfer_id else False
            else:
                voucher_id = vals.get('account_voucher_id', False)
                transaction = self.env['account.voucher'].browse(voucher_id) if voucher_id else False

            msg = record._get_log_msg(transaction, is_transfer)
            if msg:
                record.message_post(body=msg, message_type="comment", subtype="mail.mt_note")

    @api.model
    def create(self, values):
        values['memo'] = values.get('name', False)
        result = super(AccountBankStatementLineUSA, self).create(values)
        self._enable_trigger_find_possible_match(result)
        return result

    @api.multi
    def write(self, vals):
        is_auto_matching = vals.pop('auto_matching', False)
        bypass_validation = vals.pop('bypass_validation', False)
        is_apply_action = vals.pop('is_apply_action', False)

        if 'candidate_transactions_ids' in vals:
            bank_statement_line_id = self.id
            candidate_transactions = self.candidate_transactions_ids
            new_mapping_list = []
            for _, candidate_id, candidate in vals['candidate_transactions_ids']:
                if candidate and candidate['selected_item']:
                    candidate_item = candidate_transactions.browse(candidate_id)
                    if candidate_item.journal_entry_id:
                        new_mapping_list.append([0, None, {
                            'journal_entry_id': candidate_item.journal_entry_id.id,
                            'mapping_id': bank_statement_line_id
                        }])
                    else:
                        new_mapping_list.append([0, None, {
                            'batch_deposit_id': candidate_item.batch_deposit_id.id,
                            'mapping_id': bank_statement_line_id
                        }])

            if new_mapping_list:
                new_mapping_list.extend([[2, old_transaction.id, None] for old_transaction in self.mapping_transaction_ids])
                vals['mapping_transaction_ids'] = new_mapping_list

            vals.update({
                'add_transaction': 'add_transaction_input' in vals and vals.pop('add_transaction_input'),
                'new_date': 'new_date_input' in vals and vals.pop('new_date_input'),
                'new_partner_id': 'new_partner_id_input' in vals and vals.pop('new_partner_id_input'),
                'new_account_id': 'new_account_id_input' in vals and vals.pop('new_account_id_input'),
                'new_memo': 'new_memo_input' in vals and vals.pop('new_memo_input'),
                'action_type': 'match',
                'account_id': None,
                'partner_id': None,
                'split_transaction': False,
                'account_id_transfer': None,
            })

            if self.line_ids:
                vals['line_ids'] = [[2, line.id, None] for line in self.line_ids]

        elif vals.get('add_transaction_input'):
            vals.update({
                'mapping_transaction_ids': [[2, old_transaction.id, False] for old_transaction in
                                            self.mapping_transaction_ids],
                'add_transaction': vals.pop('add_transaction_input'),
                'new_date': vals.pop('new_date_input'),
                'new_partner_id': 'new_partner_id_input' in vals and vals.pop('new_partner_id_input'),
                'new_account_id': vals.pop('new_account_id_input'),
                'new_memo': 'new_memo_input' in vals and vals.pop('new_memo_input'),
                'action_type': 'match',
                'account_id': None,
                'partner_id': None,
                'split_transaction': False,
                'line_ids': None,
                'account_id_transfer': None,
            })

            if self.line_ids:
                vals['line_ids'] = [[2, line.id, None] for line in self.line_ids]
        elif 'status' in vals:
            pass
        elif len(self) == 1 and not is_auto_matching and not is_apply_action and 'account_voucher_id' not in vals and \
            ((self.action_type == 'match' and not ('candidate_transactions_ids' in vals or 'add_transaction_input' in vals
             or vals.get('action_type') in ('add', 'transfer'))) or
            (self.action_type in ('add', 'transfer') and vals.get('action_type') == 'match')):
            return


        if 'account_voucher_id' in vals:
            self._log_message_statement(vals)
        if 'account_payment_id' in vals:
            self._log_message_statement(vals, is_transfer=True)

        res = super(AccountBankStatementLineUSA, self).write(vals)
        self._validate_difference(bypass_validation)
        return res

    @api.multi
    def select_other_transaction(self, vals):
        pass

    def _enable_trigger_find_possible_match(self, record=None):

        if record:  # create a new bank statement line
            self.trigger_apply_matching(self.build_bank_statement_line_key(record.journal_id.name))
        else:
            tracking = set()
            for one_record in self:
                journal_name = one_record.journal_id.name
                if journal_name in tracking:
                    continue

                self.trigger_apply_matching(self.build_bank_statement_line_key(journal_name))

                tracking.add(journal_name)

    @api.multi
    def action_apply_item(self):
        if any(record.status != 'open' for record in self):
            raise ValidationError('You can not perform this action for the selected items.')

        for record in self:
            self._validate_apply_transaction(record)

            if record.action_type == 'add':  # Add
                account_voucher_id = self._process_apply_for_add(record)
                account_voucher_id.proforma_voucher() # validate
                record.account_voucher_id = account_voucher_id

            elif record.action_type == 'match':
                if record.add_transaction:  # Match
                    account_voucher_id = self._process_apply_for_match(record)
                    account_voucher_id.proforma_voucher()  # validate
                    record.account_voucher_id = account_voucher_id

            else:  # Transfer
                account_payment_id = self._process_apply_for_transfer(record)
                account_payment_id.post() # validate
                record.account_payment_id = account_payment_id

        self.write({'status': 'confirm', 'is_apply_action': True})

        return True

    @staticmethod
    def _validate_apply_transaction(record):
        # Check missing account
        if (record.action_type == 'add' and not record.split_transaction and not record.account_id) or \
                (record.action_type == 'transfer' and not record.account_id_transfer):
            date = datetime.strftime(fields.Date.from_string(record.date), '%m/%d/%Y')
            amount = record.journal_currency_id.symbol + str(record.amount_unsigned) \
                if record.journal_currency_id else str(record.amount_unsigned)
            raise ValidationError('Missing an account for %s %s %s' % (date, record.name, amount))

    def _process_apply_for_add(self, record):
        return self._create_account_voucher(record, record.date, record.partner_id, record.account_id,
                                            record.memo, record.amount_unsigned)

    def _process_apply_for_match(self, record):
        return self._create_account_voucher(record, record.new_date, record.new_partner_id, record.new_account_id,
                                            record.new_memo, record.new_amount)

    def _process_apply_for_transfer(self, record):
        description = record.memo if record.memo else record.name
        payment_method = self.env.ref('account.account_payment_method_manual_out')  # manual
        vals = {
            'payment_date': record.date,
            'amount': record.amount_unsigned,
            'payment_method_id': payment_method.id,
            'payment_type': 'transfer',
            'communication': description
        }
        if record.transaction_type == 'amount_paid':
            vals.update({
                'journal_id': record.journal_id.id,
                'destination_journal_id': record.account_id_transfer.id,
            })
        elif record.transaction_type == 'amount_received':
            vals.update({
                'journal_id': record.account_id_transfer.id,
                'destination_journal_id': record.journal_id.id,
            })
        return self.env[ACCOUNT_PAYMENT].create(vals)

    def _create_account_voucher(self, record, date, partner_id, account_id, memo, amount):
        vals = {
            'partner_id': partner_id.id if partner_id else False,
            'pay_now': 'pay_now',
            'date': date,
            'account_date': date,
            'payment_journal_id': record.journal_id.id,
            'company_id': record.company_id.id,
        }
        description = memo if memo else record.name
        if not record.split_transaction:
            vals['line_ids'] = [(0, 0, {'name': description,
                                        'account_id': account_id.id,
                                        'account_analytic_id': record.analytic_account_id.id,
                                        'price_unit': amount})]
        else:  # split case
            vals['line_ids'] = [(0, 0, {'name': description,
                                        'account_id': line.account_id.id,
                                        'account_analytic_id': line.analytic_account_id.id,
                                        'price_unit': line.amount}) for line in record.line_ids]

        if record.transaction_type == 'amount_paid':
            journal_id = self.env[ACCOUNT_JOURNAL].search([('type', '=', 'purchase'),
                                                           ('company_id', '=', record.company_id.id)], limit=1)
            if not journal_id:
                raise ValidationError('Please set a Journal with Purchase type.')

            account_id = self.env['account.account'].search([('deprecated', '=', False),
                                                             ('internal_type', '=', 'payable'),
                                                             ('company_id', '=', record.company_id.id)], limit=1)
            if not account_id:
                raise ValidationError('Please set a payable account.')

            vals.update({
                'voucher_type': 'purchase',
                'journal_id': journal_id.id,
                'account_id': account_id.id,
            })
        elif record.transaction_type == 'amount_received':
            journal_id = self.env[ACCOUNT_JOURNAL].search([('type', '=', 'sale'),
                                                           ('company_id', '=', record.company_id.id)], limit=1)
            if not journal_id:
                raise ValidationError('Please set a Journal with Sale type.')

            account_id = self.env['account.account'].search([('deprecated', '=', False),
                                                             ('internal_type', '=', 'receivable'),
                                                             ('company_id', '=', record.company_id.id)], limit=1)
            if not account_id:
                raise ValidationError('Please set a receivable account.')

            vals.update({
                'voucher_type': 'sale',
                'journal_id': journal_id.id,
                'account_id': account_id.id,
            })

        return self.env[ACCOUNT_VOUCHER].create(vals)

    @api.multi
    def action_exclude_item(self):
        if any(record.status != 'open' for record in self):
            raise ValidationError('You can not perform this action for the selected items.')

        self.mapped('mapping_transaction_ids').sudo().unlink()

        self.write({
            'status': 'ignore',
            'action_type': 'add',
            'mapping_transaction_ids': None,
            'bypass_validation': True,
        })
        self._enable_trigger_find_possible_match()
        return True

    @api.multi
    def action_undo_items(self):
        for record in self:
            if record.status == 'confirm':
                return self.action_undo_reviewed_item()
            elif record.status == 'ignore':
                return self.action_undo_excluded_item()
            else:
                raise ValidationError('You can not perform this action for the selected items.')

    @api.multi
    def action_undo_reviewed_item(self):
        if any(record.status != 'confirm' for record in self):
            raise ValidationError('You can not perform this action for the selected items.')

        account_payment_ids = self.mapped('account_payment_id').filtered(lambda x: x.state not in ['draft', 'cancelled'])
        if account_payment_ids:
            account_payment_ids.sudo().cancel()

        account_voucher_ids = self.mapped('account_voucher_id').filtered(lambda x: x.state not in ['draft', 'cancel'])
        if account_voucher_ids:
            account_voucher_ids.sudo().cancel_voucher()

        self.write({
            'status': 'open',
            'account_payment_id': None,
            'account_voucher_id': None,
            'bypass_validation': True,
        })
        self._enable_trigger_find_possible_match()

        # Unmark transactions, and remove this line from log
        self._remove_from_reconciliation_log()
        return True

    @api.multi
    def action_undo_excluded_item(self):
        if any(record.status != 'ignore' for record in self):
            raise ValidationError('You can not perform this action for the selected items.')

        # If we run auto matching, we don't need to clean up data because they will be destroyed in matching process
        self.write({
            'status': 'open',
            'bypass_validation': True
        })
        self._enable_trigger_find_possible_match()
        return True

    @api.multi
    def action_see_journal_entries(self):
        if self.account_voucher_id:
            domain = [('move_id', '=', self.account_voucher_id.move_id.id)]
        elif self.account_payment_id:
            domain = [('id', 'in', self.account_payment_id.move_line_ids.ids)]
        else:
            domain = []

        return {
            'name': 'Journal Items',
            'domain': domain,
            'res_model': 'account.move.line',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
        }

    @api.multi
    def _count_journal_entries(self):
        for record in self:
            if record.account_voucher_id:
                aml_ids = self.env['account.move.line'].search([('move_id', '=', record.account_voucher_id.move_id.id)])
                record.journal_entries_count = len(aml_ids)
            elif record.account_payment_id:
                record.journal_entries_count = len(record.account_payment_id.move_line_ids)
        return True

    @api.multi
    def find_other_matching_transaction(self):
        bank_statement_line_id = self.id

        batch_deposit_id_ignore, journal_entry_id_ignore = self._get_ignore_list()

        batch_deposit_candidates = self._find_candidate_deposit_list(self.amount, batch_deposit_id_ignore,
                                                                     bank_statement_line_id)
        journal_item_candidates = self._find_candidate_journal_item_list(self.amount_unsigned, journal_entry_id_ignore,
                                                                         bank_statement_line_id)

        # Clear matching table before insert
        account_matching_bank_statement_line_obj = self.env[ACCOUNT_MATCHING_BANK_STATEMENT_LINE]
        account_matching_bank_statement_line_obj.search([('mapping_id', '=', bank_statement_line_id)]).sudo().unlink()

        # Insert into matching table
        for candidate in itertools.chain(batch_deposit_candidates, journal_item_candidates):
            account_matching_bank_statement_line_obj.create(candidate)

        # Find the action and return
        action_id = self._context.get('action_id', False)
        if not action_id:
            raise ValidationError('Please click on the button again')

        [action] = self.env.ref(action_id).read()
        action.update({
            'context': self._context.copy(),
            'res_id': bank_statement_line_id,
        })

        return action

    def _get_ignore_list(self):
        batch_deposit_id_ignore = journal_entry_id_ignore = []

        for mapping in self.mapping_transaction_ids:
            if mapping.batch_deposit_id:
                batch_deposit_id_ignore.append(mapping.batch_deposit_id.id)
            elif mapping.journal_entry_id:
                journal_entry_id_ignore.append(mapping.journal_entry_id.id)

        for bank_statement_line_mapping_result in self.env[ACCOUNT_BANK_STATEMENT_LINE_MAPPING].search([]):
            if bank_statement_line_mapping_result.batch_deposit_id:
                batch_deposit_id_ignore.extend(bank_statement_line_mapping_result.batch_deposit_id.ids)
            elif bank_statement_line_mapping_result.journal_entry_id:
                journal_entry_id_ignore.extend(bank_statement_line_mapping_result.journal_entry_id.ids)

        return batch_deposit_id_ignore, journal_entry_id_ignore

    def _find_candidate_deposit_list(self, amount, batch_deposit_id_ignore, bank_statement_line_id):
        batch_deposit_domain = [
            ('journal_id', '=', self.journal_id.id),
            ('state', '!=', 'reconciled'),
            ('amount', '<=', abs(amount)),
            ('id', 'not in', batch_deposit_id_ignore)
        ]

        if amount < 0:  # send, outbound
            batch_deposit_domain.extend([('batch_type', '=', 'outbound')])
        else:  # receive, inbound
            batch_deposit_domain.extend([('batch_type', '=', 'inbound')])

        # Find the candidates of batch deposit
        account_batch_deposit_result = self.env[ACCOUNT_BATCH_DEPOSIT].search(batch_deposit_domain)

        return ({
            'batch_deposit_id': batch_deposit.id,
            'mapping_id': bank_statement_line_id,
        } for batch_deposit in account_batch_deposit_result or [])

    def _find_candidate_journal_item_list(self, amount_unsigned, journal_entry_id_ignore, bank_statement_line_id):
        filter_payment_domain = ['|', ('payment_id', '=', None), '&', ('payment_id', '!=', None),
                                 ('payment_id.batch_payment_id', '=', False)]

        journal_item_domain = [
            ('statement_line_id', '=', False),
            ('bank_reconciled', '=', False),
            ('id', 'not in', journal_entry_id_ignore),
            ('is_fund_line', '=', False),
            ('move_id.state', '=', 'posted'),
        ]
        if self.amount < 0:  # send
            account_id = self.journal_id.default_debit_account_id.id
            journal_item_domain.extend([
                ('credit', '>', 0.0),
                ('credit', '<=', amount_unsigned),
                ('account_id', '=', account_id),
            ])
        else:  # receive
            account_id = self.journal_id.default_credit_account_id.id
            journal_item_domain.extend([
                ('debit', '>', 0.0),
                ('debit', '<=', amount_unsigned),
                ('account_id', '=', account_id),
            ])

        # Can search the journal items that are created manually
        journal_item_domain.extend(filter_payment_domain)

        # Don't filter journal items by partner id
        # if self.partner_id:
        #     journal_item_domain.append(('partner_id', '=', self.partner_id.id))

        # Find the candidates of journal item (exclude open invoices and open bills)
        account_move_line_result = self.env[ACCOUNT_MOVE_LINE].search(journal_item_domain)
        return ({
            'journal_entry_id': journal_item.id,
            'mapping_id': bank_statement_line_id,
        } for journal_item in account_move_line_result or [])

    def _remove_from_reconciliation_log(self):
        """
        Uncheck all transactions + remove this line from reconciliation log
        """
        for record in self:
            record.mapped('applied_aml_ids').write({'temporary_reconciled': False})
            record.mapped('applied_batch_ids').write({'temporary_reconciled': False})
            draft_reconciliation = self.env['account.bank.reconciliation.data']\
                .search([('journal_id', '=', record.journal_id.id), ('state', '=', 'draft')])
            if draft_reconciliation:
                draft_reconciliation.write({'applied_bank_statement_line_ids': [(3, record.id)]})

    @api.model
    def update_existing_statement_line(self):
        # Mark reconciled lines as Reviewed
        reconciled_statement_lines = self.sudo().search([('journal_entry_ids', '!=', False)])
        if reconciled_statement_lines:
            reconciled_statement_lines.write({'status': 'confirm'})

        # To Review for all other statements
        review_lines = self.sudo().search([('id', 'not in', reconciled_statement_lines.ids)])
        if review_lines:
            review_lines.write({'status': 'open'})


class AccountBankStatementLineSplitAccountUSA(models.Model):
    _name = 'account.bank.statement.line.split.account'
    _description = 'This model will be used in case of we select Add action type and split account'

    account_id = fields.Many2one('account.account', string='Account', domain=[('deprecated', '=', False)])
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null')
    amount = fields.Monetary(string='Amount')
    currency_id = fields.Many2one('res.currency', string='Account Currency',
                                  default=lambda self: self.env.user.company_id.currency_id,
                                  help='Forces all lines for this account to have this account currency.')

    line_id = fields.Many2one('account.bank.statement.line', index=True)

    @api.multi
    @api.constrains('amount')
    def _check_bsl_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError('Please enter an amount is greater than 0')


class AccountBankStatementLineMappingUSA(models.Model):
    _name = 'account.bank.statement.line.mapping'
    _inherit = 'account.bank.statement.line.matching.mixin'
    _description = 'This model will be used in case of we match the bank statement line with journal item ' \
                   'or batch deposit'

    parent_status = fields.Selection(related='mapping_id.status')
    bank_reconciled = fields.Boolean(compute='_compute_bank_reconciled', store=True)

    @api.depends('journal_entry_id', 'journal_entry_id.bank_reconciled', 'batch_deposit_id', 'batch_deposit_id.state')
    def _compute_bank_reconciled(self):
        for record in self:
            if (record.journal_entry_id and record.journal_entry_id.bank_reconciled) or \
                    (record.batch_deposit_id and record.batch_deposit_id.state == 'reconciled'):
                record.bank_reconciled = True
