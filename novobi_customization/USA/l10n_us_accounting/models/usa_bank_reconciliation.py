# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.


from odoo import models, api, _, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from odoo.exceptions import UserError



class USABankReconciliation(models.AbstractModel):
    _inherit = 'account.report'
    _name = 'usa.bank.reconciliation'
    _description = 'Bank Reconciliation'

    def _get_templates(self):
        templates = super(USABankReconciliation, self)._get_templates()
        templates['line_template'] = 'l10n_us_accounting.line_template_usa_bank_reconciliation'
        templates['main_template'] = 'l10n_us_accounting.template_usa_bank_reconciliation'
        return templates

    def _get_columns_name(self, options):
        # Payment is Credit. Deposit is Debit.
        return [
            {},
            {'name': _('Date'), 'class': 'date'},
            {'name': _('Payee')},
            {'name': _('Memo')},
            {'name': _('Check Number')},
            {'name': _('Payment')},
            {'name': _('Deposit')},
            {'name': _('Reconcile')},
        ]

    def _get_aml(self, bank_reconciliation_data_id):
        account_ids = [bank_reconciliation_data_id.journal_id.default_debit_account_id.id,
                       bank_reconciliation_data_id.journal_id.default_credit_account_id.id]

        # bank_reconciled is our new field.
        # an account move line is considered reconciled if it either has Statement Line or checked bank_reconciled
        aml_ids = self.env['account.move.line'].search([('account_id', 'in', account_ids),
                                                ('date', '<=', bank_reconciliation_data_id.statement_ending_date),
                                                ('statement_line_id', '=', False),
                                                ('bank_reconciled', '=', False),
                                                ('is_fund_line', '=', False),
                                                ('move_id.state', '=', 'posted'),
                                                '|', ('payment_id', '=', False),
                                                '&', ('payment_id', '!=', False), ('payment_id.batch_payment_id', '=', False)])
        #('payment_id.batch_deposit_id', '=', False)
        #.filtered(lambda x: not x.payment_id or (x.payment_id and not x.payment_id.batch_deposit_id))
        return aml_ids

    def _get_batch_deposit(self, bank_reconciliation_data_id):
        journal_id = bank_reconciliation_data_id.journal_id

        batch_ids = self.env['account.batch.payment'].search([('journal_id', '=', journal_id.id),
                                                ('state', '!=', 'reconciled'),
                                                ('date', '<=', bank_reconciliation_data_id.statement_ending_date)])

        return batch_ids

    def _mark_applied_transaction(self, bank_reconciliation_data_id, aml_ids, batch_ids):
        """
        Mark applied transactions by default
        """
        # check newly applied transactions
        matched_transaction_ids = self.env['account.bank.statement.line'].search([
            ('status', '=', 'confirm'),
            ('id', 'not in', bank_reconciliation_data_id.applied_bank_statement_line_ids.ids),
            '|', ('applied_aml_ids', 'in', aml_ids.ids), ('applied_batch_ids', 'in', batch_ids.ids)])
        if matched_transaction_ids:
            matched_transaction_ids.mapped('applied_aml_ids').write({'temporary_reconciled': True})
            matched_transaction_ids.mapped('applied_batch_ids').write({'temporary_reconciled': True})
            bank_reconciliation_data_id.write({'applied_bank_statement_line_ids': [(4, matched.id) for matched
                                                                                   in matched_transaction_ids]})

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        bank_reconciliation_data_id = self._get_bank_reconciliation_data_id()

        aml_ids = self._get_aml(bank_reconciliation_data_id)
        batch_ids = self._get_batch_deposit(bank_reconciliation_data_id)
        self._mark_applied_transaction(bank_reconciliation_data_id, aml_ids, batch_ids)

        for line in aml_ids:
            partner_name = line.partner_id.name if line.partner_id else ''
            check_number = line.payment_id.check_number if line.payment_id and line.payment_id.check_number else ''
            columns = [self._format_date(line.date),
                       {'name': partner_name[:20],
                        'title': partner_name,
                        },
                       {'name': line.name[:30] if line.name else '',
                        'title': line.name
                        },
                       check_number,
                       self.format_value(line.credit) if line.credit > 0 else '',
                       self.format_value(line.debit) if line.debit > 0 else '',
                       {'name': False, 'blocked': line.temporary_reconciled,
                        'debit': line.debit,
                        'credit': line.credit}]
            caret_type = 'account.move'
            if line.invoice_id:
                caret_type = 'account.invoice.in' if line.invoice_id.type in (
                'in_refund', 'in_invoice') else 'account.invoice.out'
            elif line.payment_id:
                caret_type = 'account.payment'
            lines.append({
                        'id': line.id,
                        'name': line.move_id.name,
                        'caret_options': caret_type,
                        'model': 'account.move.line',
                        'columns': [type(v) == dict and v or {'name': v} for v in columns],
                        'level': 1,
                    })

        # Batch deposit is in Deposit side.
        for line in batch_ids:
            columns = [self._format_date(line.date),
                       '',
                       {'name': line.name[:30] if line.name else '',
                        'title': line.name
                        },
                       '', '',
                       self.format_value(line.amount),
                       {'name': False, 'blocked': line.temporary_reconciled,
                        'debit': line.amount,
                        'credit': 0}]
            lines.append({
                        'id': line.id,
                        'name': line.name,
                        'caret_options': 'account.batch.payment',
                        'model': 'account.batch.payment',
                        'columns': [type(v) == dict and v or {'name': v} for v in columns],
                        'level': 1,
                    })

        if not lines:
            lines.append({
                'id': 'base',
                'model': 'base',
                'level': 0,
                'class': 'o_account_reports_domain_total',
                'columns': [{'name': v} for v in ['', '', '', '', '', '', '']],
            })
        return lines

    @api.model
    def _get_report_name(self):
        bank_reconciliation_data_id = self._get_bank_reconciliation_data_id()

        return bank_reconciliation_data_id.journal_id.name

    def _get_reports_buttons(self):
        return []

    @api.multi
    def get_html(self, options, line_id=None, additional_context=None):
        bank_reconciliation_data_id = self._get_bank_reconciliation_data_id()

        if additional_context == None:
            additional_context = {}

        beginning_balance = bank_reconciliation_data_id.beginning_balance
        ending_balance = bank_reconciliation_data_id.ending_balance

        additional_context.update({
            'today': self._format_date(bank_reconciliation_data_id.statement_ending_date),
            'beginning_balance': beginning_balance,
            'ending_balance': ending_balance,
            'formatted_beginning': self.format_value(beginning_balance),
            'formatted_ending': self.format_value(ending_balance),
            'bank_reconciliation_data_id': bank_reconciliation_data_id.id
        })

        options['currency_id'] = bank_reconciliation_data_id.currency_id.id
        options['multi_company'] = None

        return super(USABankReconciliation, self).get_html(options, line_id=line_id,
                                                           additional_context=additional_context)

    def _format_date(self, date):
        return datetime.strftime(date, '%m/%d/%Y')

    def _get_bank_reconciliation_data_id(self):
        bank_reconciliation_data_id = None
        bank_id = self.env.context.get('bank_reconciliation_data_id', False)

        params = self.env.context.get('params', False)

        if not bank_id and params and params.get('action', False):
            action_obj = self.env['ir.actions.client'].browse(params['action'])
            bank_id = action_obj.params.get('bank_reconciliation_data_id', False)

        if bank_id:
            bank_reconciliation_data_id = self.env['account.bank.reconciliation.data'].browse(bank_id)

        if not bank_reconciliation_data_id:
            raise UserError(_('Cannot get Bank\'s information.'))

        if bank_reconciliation_data_id.state == 'reconciled':
            raise UserError(_('You can not access this screen anymore because it is already reconciled.'))

        return bank_reconciliation_data_id

    @api.multi
    def open_batch_deposit_document(self, options, params=None):
        if not params:
            params = {}
        ctx = self.env.context.copy()
        ctx.pop('id', '')
        batch_id = params.get('id')
        if batch_id:
            view_id = self.env['ir.model.data'].get_object_reference('account_batch_payment', 'view_batch_payment_form')[1]
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'tree',
                'view_mode': 'form',
                'views': [(view_id, 'form')],
                'res_model': 'account.batch.payment',
                'view_id': view_id,
                'res_id': batch_id,
                'context': ctx,
            }
