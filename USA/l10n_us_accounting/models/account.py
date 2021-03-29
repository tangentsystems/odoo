# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..models.model_const import (
    ACCOUNT_BANK_STATEMENT_LINE,
    ACCOUNT_BANK_STATEMENT_LINE_SPLIT_ACCOUNT,
)

# TODO: Review new conditions in v12
class AccountReconcileModelUSA(models.Model):
    _name = 'account.reconcile.model'
    _inherit = ['account.reconcile.model', 'account.caching.mixin.usa']
    _order = 'sequence, id'

    # Override
    name = fields.Char(string='Rule')
    rule_type = fields.Selection(default='writeoff_suggestion')

    payee = fields.Many2one('res.partner', string='Payee')
    line_ids = fields.One2many('account.reconcile.model.line', 'line_id', string='Bank rule lines')

    label = fields.Char(string='Memo')
    internal_transfer = fields.Boolean(string='Internal Transfer', default=False)

    # Override old attribute because they are moved to account.reconcile.model.line
    amount_type = fields.Selection([
        ('fixed', 'Amount($)'),
        ('percentage', 'Percentage(%)')
    ], required=False, default='percentage')
    amount = fields.Float(required=False)

    account_id_transfer = fields.Many2one('account.journal', string='Account', ondelete='set null', domain=[('type', '=', 'bank')])

    @api.onchange('match_nature')
    def _onchange_payee(self):
        domain = [('parent_id', '=', False)]

        if self.match_nature == 'amount_received':
            domain.append(('customer', '=', 1))
        elif self.match_nature == 'amount_paid':
            domain.append(('supplier', '=', 1))
        return {
            'domain': {'payee': domain},
        }

    @api.onchange('internal_transfer', 'has_second_line')
    def _onchange_has_second_line(self):
        if self.internal_transfer:
            self.has_second_line = self.line_ids = self.payee = self.account_id = self.analytic_account_id = self.analytic_tag_ids = False
        else:
            self.account_id_transfer = None

        if not self.has_second_line:
            self.line_ids = None
        else:
            self.account_id = self.account_id_transfer = self.analytic_account_id = self.analytic_tag_ids = None

    @api.onchange('amount_type')
    def _onchange_amount_type(self):
        if self.line_ids:
            if self.amount_type == 'percentage':
                for line_id in self.line_ids:
                    line_id.amount = 0
            elif self.amount_type == 'fixed':
                for line_id in self.line_ids:
                    line_id.amount_percentage = 0

    @api.onchange('name')
    def onchange_name(self):
        pass

    @api.multi
    @api.constrains('internal_transfer', 'account_id', 'account_id_transfer', 'payee', 'has_second_line', 'label')
    def _validate_at_least_value(self):
        parameter_checking = ['internal_transfer', 'account_id', 'account_id_transfer', 'payee', 'has_second_line', 'label']
        for record in self:
            if not any((getattr(record, parameter) for parameter in parameter_checking)):
                raise ValidationError('You need to set at least one field to save the rule')

            if record.internal_transfer and not record.account_id_transfer:
                raise ValidationError('Please select an account for Internal Transfer')

            if record.has_second_line and not record.line_ids:
                raise ValidationError('Please add at least one line item for this rule')

    @api.multi
    @api.constrains('line_ids')
    def _check_amount(self):
        for record in self:
            if record.has_second_line:
                if record.line_ids:
                    if record.amount_type == 'percentage':
                        total_percentage = 0
                        for line in record.line_ids:
                            if not 0.01 <= line.amount_percentage <= 99.99:
                                raise ValidationError('Please enter a percentage between 0.01 and 99.99')
                            total_percentage += line.amount_percentage
                            # Reset amount to default because user select amount percentage
                            line.amount = 0.0
                        if total_percentage != 100.0: # Amount percentage is not 0%
                            raise ValidationError('Split line percentages must add up exactly to 100%')
                    elif record.amount_type == 'fixed':
                        for line in record.line_ids:
                            if line.amount <= 0:
                                raise ValidationError('Please enter an amount is greater than 0')
                            # Reset amount_percentage to default because user select amount
                            line.amount_percentage = 0.0
                else:
                    raise ValidationError('Please add at least one line item for this rule')

    @api.model
    def create(self, values):
        self.env.cr.execute("""SELECT max(sequence) + 1 as max_sequence FROM account_reconcile_model;""")
        max_sequence = self.env.cr.dictfetchall()[0]
        if max_sequence.get('max_sequence'):
            values['sequence'] = max_sequence.get('max_sequence')
        result = super(AccountReconcileModelUSA, self).create(values)

        self._enable_trigger_apply_bank_rule(result)

        return result

    @api.multi
    def write(self, vals):
        old_match_journal = {}
        for record in self:
            old_match_journal[record.id] = record.match_journal_ids

        result = super(AccountReconcileModelUSA, self).write(vals)

        for record in self:
            new_ids = record.match_journal_ids
            old_ids = old_match_journal[record.id]
            change_journals = (new_ids - old_ids) + (old_ids - new_ids)
            record._enable_trigger_apply_bank_rule(change_journals=change_journals)
        return result

    @api.multi
    def unlink(self):
        # Try to revert data that is applied to bank statement line from bank rule
        bank_statement_line_objs = self.env[ACCOUNT_BANK_STATEMENT_LINE]
        for record in self:
            mapping_result = bank_statement_line_objs.search([
                ('bank_rule_apply', '=', record.id),
                ('status', '=', 'open'),
            ])

            if mapping_result:
                # Clean up old data
                self._clean_up_old_data(mapping_result)

        self._enable_trigger_apply_bank_rule()
        result = super(AccountReconcileModelUSA, self).unlink()
        return result

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

    def _enable_trigger_apply_bank_rule(self, new_record=None, change_journals=None):
        if new_record:
            journal_ids = new_record.match_journal_ids if new_record.match_journal_ids else \
                self.env['account.journal'].search([('type', 'in', ['bank', 'cash'])])
            for journal_id in journal_ids:
                self.trigger_apply_matching(self.build_bank_rule_key(journal_id.name))
        else:
            tracking = set()

            if change_journals:
                journal_ids = change_journals
            else:
                journal_ids = self.match_journal_ids if self.match_journal_ids else \
                    self.env['account.journal'].search([('type', 'in', ['bank', 'cash'])])

            for journal_id in journal_ids:
                journal_name = journal_id.name
                if journal_name in tracking:
                    continue
                self.trigger_apply_matching(self.build_bank_rule_key(journal_name))

                tracking.add(journal_name)

    ########################################################
    # INITIAL FUNCTION
    ########################################################
    @api.model
    def update_bank_rule_type(self):
        # Delete Invoices Matching Rule
        try:
            invoice_rule = self.env.ref('account.reconciliation_model_default_rule')
            if invoice_rule:
                invoice_rule.unlink()
        except:
            pass

        # Change bank rule type
        records = self.sudo().search([])
        records.write({'rule_type': 'writeoff_suggestion'})



class AccountReconcileModelLine(models.Model):
    _name = 'account.reconcile.model.line'
    _description = 'Preset to create bank rule lines'

    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', required=True,
                                 domain=[('deprecated', '=', False)])
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    amount = fields.Monetary(string='Amount')
    amount_percentage = fields.Float(string='Amount(%)', digits=0)

    currency_id = fields.Many2one('res.currency', string='Account Currency',
                                  default=lambda self: self.env.user.company_id.currency_id,
                                  help='Forces all lines for this account to have this account currency.')

    line_id = fields.Many2one('account.reconcile.model', string='Bank rule', index=True, ondelete='cascade')

    @api.onchange('amount_percentage')
    def _onchange_amount_percentage(self):
        if self.amount_percentage < 0 or self.amount_percentage > 100.0:
            raise ValidationError('Please enter a percentage between 0.01 and 99.99')
