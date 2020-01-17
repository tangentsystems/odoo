# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

import ast
import logging
import time

from odoo import api, fields, models
from odoo.tools import safe_eval, formatLang

from ..models.model_const import (
    ACCOUNT_RECONCILE_MODEL,
    ACCOUNT_BANK_STATEMENT_LINE,
    ACCOUNT_MOVE_LINE,
    ACCOUNT_BANK_STATEMENT_LINE_MAPPING,
    ACCOUNT_BATCH_DEPOSIT,
    ACCOUNT_BANK_RECONCILIATION_DATA,
    ACCOUNT_PAYMENT,
    ACCOUNT_BANK_STATEMENT_LINE_SPLIT_ACCOUNT,
)
from ..utils import action_utils
from ..utils import bank_statement_line_utils

_logger = logging.getLogger(__name__)


class AccountJournalUSA(models.Model):
    _name = 'account.journal'
    _inherit = ['account.journal', 'account.caching.mixin.usa']

    @api.multi
    def get_journal_dashboard_datas(self):
        data = super(AccountJournalUSA, self).get_journal_dashboard_datas()
        if self.type in ['bank', 'cash']:
            previous_reconciliation = self.env[ACCOUNT_BANK_RECONCILIATION_DATA].search(
                [('journal_id', '=', self.id), ('state', '=', 'reconciled')], order='id desc', limit=1)
            ending_balance = previous_reconciliation and previous_reconciliation.ending_balance or 0.0
            currency = self.currency_id or self.company_id.currency_id
            new_last_balance = formatLang(self.env, currency.round(ending_balance), currency_obj=currency)

            data.update({
                'number_for_reviews': self.env[ACCOUNT_BANK_STATEMENT_LINE].search_count([
                    ('journal_id', '=', self.id), ('status', '=', 'open')
                ]),
                'new_last_balance': new_last_balance,
            })
        else:
            data.update({
                'number_for_reviews': 0,
                'new_last_balance': 0,
            })
        return data

    @api.multi
    def open_action_reconciliation(self):
        get_context_env = self.env.context.get
        action_name = get_context_env('action_name')
        if not action_name:
            return False

        ctx = self._context.copy()
        ctx.pop('group_by', None)
        ir_model_obj = self.env['ir.model.data']
        model, action_id = ir_model_obj.get_object_reference('l10n_us_accounting', action_name)
        [action] = self.env[model].browse(action_id).read()

        domain = ast.literal_eval(action['domain'])
        domain.append(('journal_id', '=', self.id))

        action.update({
            'context': ctx,
            'display_name': ' '.join((action['name'], 'from', self.name)),
            'domain': domain,
        })

        if action_name == 'action_for_review_usa':
            self._process_for_review()

        return action

    def _process_for_review(self):
        # Apply bank rule
        self._apply_bank_rule_to_bank_statement()

        # Map journal entries or batch deposit
        self._mapping_bank_statement_line_with_transaction()

        # Update caching bank statement line
        self.enable_caching(self.build_bank_statement_line_key(self.name))

    def _get_conditions_from_bank_rule(self, rule):
        query = """
          SELECT
            st_line.id                              AS id
            FROM account_bank_statement_line st_line
            LEFT JOIN account_journal journal       ON journal.id = st_line.journal_id
            LEFT JOIN res_company company           ON company.id = st_line.company_id
            WHERE """
        params = []
        sub_query = []

        # Filter on Company
        if rule.company_id:
            sub_query.append(' st_line.company_id = %s ')
            params += [rule.company_id.id]

        # # Filter on journals.
        if rule.match_journal_ids:
            sub_query.append(' st_line.journal_id IN %s ')
            params += [tuple(rule.match_journal_ids.ids)]

        # Filter on amount nature.
        if rule.match_nature != 'both':
            sub_query.append(' st_line.transaction_type = %s ')
            params += [rule.match_nature]

        # Filter on amount.
        if rule.match_amount:
            if rule.match_amount == 'lower':
                sub_query.append(' st_line.amount_unsigned < %s ')
                params += [rule.match_amount_max]
            elif rule.match_amount == 'greater':
                sub_query.append(' st_line.amount_unsigned > %s ')
                params += [rule.match_amount_min]
            else:
                # if self.match_amount == 'between'
                sub_query.append(' st_line.amount_unsigned BETWEEN %s AND %s ')
                params += [rule.match_amount_min, rule.match_amount_max]

        # Filter on label.
        if rule.match_label == 'contains':
            sub_query.append(' st_line.name ILIKE %s ')
            params += ['%%%s%%' % rule.match_label_param]
        elif rule.match_label == 'not_contains':
            sub_query.append(' st_line.name NOT ILIKE %s ')
            params += ['%%%s%%' % rule.match_label_param]
        elif rule.match_label == 'match_regex':
            sub_query.append(' st_line.name ~ %s ')
            params += [rule.match_label_param]

        if sub_query:
            query += ' AND '.join(sub_query)

            self._cr.execute(query, params)
            query_res = self._cr.dictfetchall()

            return [i['id'] for i in query_res]

        return []

    def _apply_bank_rule_to_bank_statement(self):
        start_time = time.time()
        bank_rule_key = self.build_bank_rule_key(self.name)
        bank_statement_line_key = self.build_bank_statement_line_key(self.name)
        if not self.is_apply_process(bank_rule_key) and not self.is_apply_process(bank_statement_line_key):
            _logger.info('Do not run apply bank rule to bank statement because use cached')
            return

        # Find all available bank statement line
        bank_statement_line_objs = self.env[ACCOUNT_BANK_STATEMENT_LINE]

        # Check if size of bank_statement_line_objs
        if not bank_statement_line_objs.search([('status', '=', 'open')], limit=1):
            self.enable_caching(bank_rule_key)
            _logger.info('Do not run apply bank rule to bank statement because no bank statement line in open')
            return

        journal_id = self.id
        company_id = self.company_id.id
        mapping_ids = set()

        # Find all bank rules
        available_bank_rules = self.env[ACCOUNT_RECONCILE_MODEL].search(['&', ('company_id', '=', company_id),
                                                                         '|', ('match_journal_ids', '=', False),
                                                                         ('match_journal_ids', 'in', journal_id)])
        if not available_bank_rules:
            clear_lines = bank_statement_line_objs.search([('journal_id', '=', journal_id),
                                                           ('bank_rule_apply', '!=', False)])
            self._clean_up_old_data(clear_lines)

        for bank_rule in available_bank_rules:
            stmt_line_ids = self._get_conditions_from_bank_rule(bank_rule)

            mapping_result = bank_statement_line_objs.browse(stmt_line_ids).filtered(
                lambda r: r.id not in mapping_ids)

            # Find old applied bank rule that don't match in this time
            old_mapping_result = bank_statement_line_objs.search([
                ('company_id', '=', company_id),
                ('bank_rule_apply', '=', bank_rule.id),
                ('id', 'not in', mapping_result.ids)
            ])

            if old_mapping_result:
                # Clean up old data
                self._clean_up_old_data(old_mapping_result)

            if mapping_result:
                # Clean up data before filled
                self._clean_up_old_data(mapping_result)

                # Copy values of bank rules to bank statement mapping list: account, memo, payee, split (if have)
                self._transfer_data_to_bank_statement_line(bank_rule, mapping_result)

                # Update IDs list of mapping
                mapping_ids = mapping_ids | set(mapping_result.ids)

        # Update caching to prevent to run again in the next time when user access this page
        self.enable_caching(bank_rule_key)
        _logger.info('Bank rule apply execution: %s' % (time.time() - start_time))

    def _clean_up_old_data(self, bank_statement_lines):
        split_account_obj = self.env[ACCOUNT_BANK_STATEMENT_LINE_SPLIT_ACCOUNT]
        for line in bank_statement_lines:
            if line.bank_rule_apply_tracking:
                update_values = {column: None for column in line.bank_rule_apply_tracking.split(',')}
                if 'split_transaction' in update_values:
                    # Set is_delete flag in split.account
                    split_accounts = split_account_obj.browse(line.line_ids.ids)
                    split_accounts.sudo().unlink()

                if 'action_type' in update_values:
                    update_values['action_type'] = 'add'  # Reset to default value

                update_values.update({
                    'bypass_validation': True,
                    'auto_matching': True,
                })
                line.write(update_values)

    def _transfer_data_to_bank_statement_line(self, bank_rule, mapping_result):

        # update_values variable is used for tracking the columns that will be transfer data
        update_values = {
            'bank_rule_apply': bank_rule.id,
            'bypass_validation': True,
            'auto_matching': True,
        }
        bank_rule_apply_tracking = ['bank_rule_apply']

        if bank_rule.label:
            update_values['memo'] = bank_rule.label
            bank_rule_apply_tracking.append('memo')

        if bank_rule.internal_transfer:
            # For displaying purpose only
            # TODO: how to determine the side of transaction from bank rule?
            account_id = bank_rule.account_id_transfer.default_credit_account_id  # send
            # if bank_rule.type == 'receive':
            #     account_id = bank_rule.account_id_transfer.default_debit_account_id

            update_values.update({
                'account_id_transfer': bank_rule.account_id_transfer.id,
                'action_type': 'transfer',
                'account_id': account_id.id,
            })
            bank_rule_apply_tracking.extend(('action_type', 'account_id_transfer'))
        else:
            if bank_rule.payee:
                update_values['partner_id'] = bank_rule.payee.id
                bank_rule_apply_tracking.append('partner_id')

                # Just turn on this trigger in case of payee because we need this value to run find possible match
                self.trigger_apply_matching(self.build_bank_statement_line_key(self.name))

            if bank_rule.has_second_line:
                update_values['split_transaction'] = True
                bank_rule_apply_tracking.append('split_transaction')

                if bank_rule.amount_type == 'fixed':
                    line_ids = ([0, '', {'amount': line_id.amount, 'account_id': line_id.account_id.id,
                                         'analytic_account_id': line_id.analytic_account_id.id,
                                         'analytic_tag_ids': [(6, 0, line_id.analytic_tag_ids.ids)],
                                         'currency_id': line_id.currency_id.id}] for line_id in bank_rule.line_ids)
                    update_values['line_ids'] = line_ids
                    bank_rule_apply_tracking.append('line_ids')
                else:  # Default is percentage
                    for mapping in mapping_result:
                        line_ids = ([0, '', {'amount': mapping.amount_unsigned * line_id.amount_percentage / 100.0,
                                             'analytic_account_id': line_id.analytic_account_id.id,
                                             'analytic_tag_ids': [(6, 0, line_id.analytic_tag_ids.ids)],
                                             'account_id': line_id.account_id.id, 'currency_id': line_id.currency_id.id}]
                                    for line_id in bank_rule.line_ids)
                        mapping.write({'line_ids': line_ids})
            else:
                update_values.update({'account_id': bank_rule.account_id.id,
                                      'analytic_account_id': bank_rule.analytic_account_id.id,
                                      'analytic_tag_ids': [(6, 0, bank_rule.analytic_tag_ids.ids)]})
                bank_rule_apply_tracking.extend(['account_id', 'analytic_account_id', 'analytic_tag_ids'])

        update_values['bank_rule_apply_tracking'] = ','.join(bank_rule_apply_tracking)
        mapping_result.write(update_values)

    def _mapping_bank_statement_line_with_transaction(self):
        """
        This method will map bank statement line with the transactions such as journal item or batch deposit
        """

        batch_deposit_key = self.build_batch_deposit_key(self.name)
        bank_statement_line_key = self.build_bank_statement_line_key(self.name)
        journal_item_key = self.build_journal_item_key(self.name)

        if self.is_apply_process(journal_item_key) or self.is_apply_process(bank_statement_line_key):
            mapping_ids, processed_bank_statement_line = self._matching_with_check_payment()
        else:
            processed_bank_statement_line = []
            mapping_ids = set()
            _logger.info('Do not map check payment with bank statement')

        if self.is_apply_process(batch_deposit_key) or self.is_apply_process(bank_statement_line_key):
            processed_bank_statement_line = self._matching_with_batch_deposit(processed_bank_statement_line)

            # Update caching for batch deposit
            self.enable_caching(batch_deposit_key)
        else:
            _logger.info('Do not map batch deposit with bank statement')

        if self.is_apply_process(journal_item_key) or self.is_apply_process(bank_statement_line_key):
            self._matching_with_journal_item(mapping_ids, processed_bank_statement_line)

            # Update caching for journal item
            self.enable_caching(journal_item_key)
        else:
            _logger.info('Do not map journal item with bank statement')

    def _matching_with_check_payment(self):

        journal_id = self.id
        bank_statement_line_result = self.env[ACCOUNT_BANK_STATEMENT_LINE].search([
            ('status', '=', 'open'),
            ('journal_id', '=', journal_id),
            ('amount', '<', 0),
        ])

        processed_bank_statement_line = []
        mapping_column = 'journal_entry_id'
        mapping_ids = set()
        account_payment_obj = self.env[ACCOUNT_PAYMENT]
        account_move_line_obj = self.env[ACCOUNT_MOVE_LINE]
        account_bank_statement_line_mapping_obj = self.env[ACCOUNT_BANK_STATEMENT_LINE_MAPPING]
        debit_account_id = self.default_debit_account_id.id
        journal_id = self.id

        for bank_statement_line in bank_statement_line_result:
            description = bank_statement_line.name
            if bank_statement_line_utils.is_check_statement(description):
                check_number = bank_statement_line_utils.extract_check_number(description)
                if not check_number:
                    continue

                # We add bank_statement_line_id to stop finding possible match
                # if there's check number in description and there's no matching check payment in the system
                processed_bank_statement_line.append(bank_statement_line.id)

                domain = [
                    ('journal_id', '=', journal_id),
                    ('payment_type', '=', 'outbound'),
                    ('payment_method_id.name', '=', 'Checks'),
                    ('amount', '=', bank_statement_line.amount_unsigned),
                    ('check_number_text', '=', check_number),
                ]

                account_payment_result = account_payment_obj.search(domain).filtered(lambda r: r.id not in mapping_ids)
                mapping_id = None

                for account_payment_data in account_payment_result:
                    # In case of we have a lot of payments, we will get the payment in turn
                    duration = fields.Date.from_string(bank_statement_line.date) - \
                               fields.Date.from_string(account_payment_data.payment_date)

                    # Days between transaction in Odoo and bank statement line is not more than 180 days
                    if 0 <= duration.days <= 180:
                        # Find journal item
                        domain = [
                            ('statement_line_id', '=', False),
                            ('is_fund_line', '=', False),
                            ('bank_reconciled', '=', False),
                            ('move_id.state', '=', 'posted'),
                            ('payment_id', '=', account_payment_data.id),
                            ('credit', '=', bank_statement_line.amount_unsigned),
                            ('account_id', '=', debit_account_id),
                            ('journal_id', '=', journal_id),
                        ]

                        account_move_line_result = account_move_line_obj.search(domain)

                        mapping_id, processed_bank_statement_line_id = self._process_mapping_result(
                            account_move_line_result,
                            bank_statement_line,
                            account_bank_statement_line_mapping_obj,
                            mapping_column,
                            True,  # this is a journal item
                        )

                        if mapping_id:
                            mapping_ids.add(mapping_id)

                if not mapping_id:
                    # Reset bank statement line if we cannot find the possible match with check payment
                    self._clean_data_before_matching(bank_statement_line)

        return mapping_ids, processed_bank_statement_line

    def _matching_with_batch_deposit(self, processed_bank_statement_line):

        journal_id = self.id
        bank_statement_line_result = self.env[ACCOUNT_BANK_STATEMENT_LINE].search([
            ('status', '=', 'open'),
            ('journal_id', '=', journal_id),
            ('action_type', '!=', 'transfer'),
            ('partner_id', '=', None),
            ('id', 'not in', processed_bank_statement_line),
        ])

        mapping_column = 'batch_deposit_id'
        mapping_ids = set()
        account_bank_statement_line_mapping_obj = self.env[ACCOUNT_BANK_STATEMENT_LINE_MAPPING]
        account_batch_deposit_obj = self.env[ACCOUNT_BATCH_DEPOSIT]
        order = 'date desc, id asc'

        for bank_statement_line in bank_statement_line_result:
            # receive
            domain = [
                ('journal_id', '=', journal_id),
                ('state', '!=', 'reconciled'),
                ('amount', '=', bank_statement_line.amount_unsigned),
                ('date', '<=', bank_statement_line.date),
            ]

            if bank_statement_line.amount < 0:  # send, outbound
                domain.extend([('batch_type', '=', 'outbound')])
            else:  # receive, inbound
                domain.extend([('batch_type', '=', 'inbound')])

            account_batch_deposit_result = account_batch_deposit_obj.search(domain, order=order).filtered(
                lambda r: r.id not in mapping_ids)

            mapping_id, processed_bank_statement_line_id = self._process_mapping_result(
                account_batch_deposit_result,
                bank_statement_line,
                account_bank_statement_line_mapping_obj,
                mapping_column,
                False,  # this is not a journal item
            )

            if mapping_id:
                mapping_ids.add(mapping_id)

            if processed_bank_statement_line_id:
                processed_bank_statement_line.append(processed_bank_statement_line_id)

        return processed_bank_statement_line

    def _matching_with_journal_item(self, mapping_ids, processed_bank_statement_line):
        # Find all bank statement line in open status
        bank_statement_line_result = self.env[ACCOUNT_BANK_STATEMENT_LINE].search([
            ('status', '=', 'open'),
            ('journal_id', '=', self.id),
            ('id', 'not in', processed_bank_statement_line),
        ]).sorted(key=lambda r: (not r.partner_id, r.date, r.sequence, r.id))

        mapping_column = 'journal_entry_id'
        account_bank_statement_line_mapping_obj = self.env[ACCOUNT_BANK_STATEMENT_LINE_MAPPING]
        account_move_line_obj = self.env[ACCOUNT_MOVE_LINE]
        credit_account_id = self.default_credit_account_id.id
        debit_account_id = self.default_debit_account_id.id
        order = 'date desc, id asc'
        filter_payment_domain = ['|', ('payment_id', '=', None),
                                 '&', ('payment_id', '!=', None), ('payment_id.batch_payment_id', '=', False)]

        # Search applied aml, these should NOT be considered as matched items
        self.env.cr.execute("SELECT account_move_line_id from applied_aml_bsl_table;")
        applied_aml_ids = [r[0] for r in self.env.cr.fetchall()]

        for bank_statement_line in bank_statement_line_result:
            domain = [
                ('statement_line_id', '=', False),
                ('is_fund_line', '=', False),
                ('bank_reconciled', '=', False),
                ('move_id.state', '=', 'posted'),
                ('date', '<=', bank_statement_line.date),
                ('id', 'not in', applied_aml_ids),
            ]
            if bank_statement_line.amount < 0:  # send
                domain.extend([
                    ('credit', '=', bank_statement_line.amount_unsigned),
                    ('account_id', '=', debit_account_id),
                ])
            else:  # receive
                domain.extend([
                    ('debit', '=', bank_statement_line.amount_unsigned),
                    ('account_id', '=', credit_account_id),
                ])

            if bank_statement_line.partner_id:
                domain.append(('partner_id', '=', bank_statement_line.partner_id.id))

            domain.extend(filter_payment_domain)
            if bank_statement_line.action_type == 'transfer':
                # just find journal item as internal transfer
                account_move_line_result = account_move_line_obj.search(domain, order=order).filtered(
                    lambda r: r.id not in mapping_ids and r.payment_id.payment_type == 'transfer')
            else:
                account_move_line_result = account_move_line_obj.search(domain, order=order).filtered(
                    lambda r: r.id not in mapping_ids)

            mapping_id, processed_bank_statement_line_id = self._process_mapping_result(
                account_move_line_result,
                bank_statement_line,
                account_bank_statement_line_mapping_obj,
                mapping_column,
                True,  # this is a journal item
            )

            if mapping_id:
                mapping_ids.add(mapping_id)

    def _process_mapping_result(self, matching_result, bank_statement_line, account_bank_statement_line_mapping_obj,
                                mapping_column, is_journal_item):

        self._clean_data_before_matching(bank_statement_line)

        number_of_result = len(matching_result)
        if number_of_result == 1:
            return self._create_mapping_data(matching_result, bank_statement_line,
                                             account_bank_statement_line_mapping_obj, mapping_column)

        elif number_of_result > 1:
            try:
                # Find the item that has the date is nearest with the date of bank statement line
                if is_journal_item:
                    candidate_item = next(item for item in matching_result if
                                          item.date <= bank_statement_line.date and item.parent_state == 'posted')
                else:
                    candidate_item = next(item for item in matching_result if
                                          item.date <= bank_statement_line.date)

                return self._create_mapping_data(candidate_item, bank_statement_line,
                                                 account_bank_statement_line_mapping_obj, mapping_column)
            except StopIteration:
                pass

        return None, None

    @staticmethod
    def _create_mapping_data(matching_result, bank_statement_line, account_bank_statement_line_mapping_obj,
                             mapping_column):

        # create mapping data
        account_bank_statement_line_mapping_obj.create({
            mapping_column: matching_result.id,
            'mapping_id': bank_statement_line.id,
        })

        # match bank statement line with this matching result
        bank_statement_line.write({
            'action_type': 'match',
            'bypass_validation': True,
            'auto_matching': True,
        })

        return matching_result.id, bank_statement_line.id

    @staticmethod
    def _clean_data_before_matching(bank_statement_line):
        if bank_statement_line.mapping_transaction_ids:
            # Clean old mapping data
            bank_statement_line.mapping_transaction_ids.sudo().unlink()

        bank_statement_line.write({
            'action_type': 'add',
            'add_transaction': False,
            'new_date': None,
            'new_account_id': None,
            'new_partner_id': None,
            'new_memo': None,
            'mapping_transaction_ids': None,
            'added_or_matched_description': None,
            'account_id_transfer': None,
            'bypass_validation': True,
            'auto_matching': True,
        })

    @api.multi
    def action_usa_reconcile(self):
        """
        Either open a popup to set Ending Balance & Ending date
        or go straight to Reconciliation Screen
        """
        draft_reconciliation = self.env['account.bank.reconciliation.data']. \
            search([('journal_id', '=', self.id), ('state', '=', 'draft')], limit=1)

        # If a draft reconciliation is found, go to that screen
        if draft_reconciliation:
            return draft_reconciliation.open_reconcile_screen()

        # open popup
        action = self.env.ref('l10n_us_accounting.action_bank_reconciliation_data_popup').read()[0]
        action['context'] = {'default_journal_id': self.id}
        return action

    @api.multi
    def open_action(self):
        """return action based on type for related journals"""
        action = super(AccountJournalUSA, self).open_action()
        search_view_id = self._context.get('search_view_id', False)
        if search_view_id:
            account_invoice_filter = self.env.ref(search_view_id, False)
            if account_invoice_filter:
                action['search_view_id'] = (account_invoice_filter.id, account_invoice_filter.name)

        return action

    @api.multi
    def action_create_new_credit_note(self):
        """ This is a new method, call action_create_new method from super
            Because action returned from action_create_new method use view_id for invoice and bill only,
            so we change the view_id to open the correct credit note form
        """
        action = super(AccountJournalUSA, self).action_create_new()
        if action['view_id'] == self.env.ref('account.invoice_form').id:
            action['view_id'] = self.env.ref('l10n_us_accounting.credit_note_form_usa').id
        elif action['view_id'] == self.env.ref('account.invoice_supplier_form').id:
            action['view_id'] = self.env.ref('l10n_us_accounting.credit_note_supplier_form_usa').id
        return action

    @api.multi
    def open_payments_action(self, payment_type, mode=False):
        action = super(AccountJournalUSA, self).open_payments_action(payment_type, mode)
        if action:
            display_name = self.env.context.get('display_name', False)
            if display_name:
                action['display_name'] = display_name

            domains = action['domain']
            # index = domain_utils.find_domain_by_field(domains, 'payment_type')
            # if index > -1:
            #    del domains[index]

            if payment_type == 'inbound':
                # domains.append(('partner_type', '=', 'customer'))
                action_utils.update_views(action, 'tree', self.env.ref('account.view_account_payment_tree').id)
            elif payment_type == 'outbound':
                # domains.append(('partner_type', '=', 'supplier'))
                action_utils.update_views(action, 'tree', self.env.ref('account.view_account_supplier_payment_tree').id)
            elif payment_type == 'transfer':
                # domains.append(('payment_type', '=', 'transfer'))
                action_utils.update_views(action, 'tree',
                                          self.env.ref('l10n_us_accounting.view_account_internal_transfer_tree_usa').id)
            return action
