# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

from ..models.model_const import ACCOUNT_BANK_STATEMENT_LINE_MAPPING


class AccountBatchDepositUSA(models.Model):
    _name = 'account.batch.payment'
    _inherit = ['account.batch.payment', 'account.caching.mixin.usa']

    temporary_reconciled = fields.Boolean()
    fund_line_ids = fields.One2many('account.batch.deposit.fund.line', 'batch_deposit_id')

    @api.multi
    @api.constrains('amount')
    def _check_deposit_amount(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(_("Batch Deposit amount cannot be negative."))

    @api.multi
    def update_temporary_reconciled(self, ids, checked):
        return self.browse(ids).write({'temporary_reconciled': checked})

    @api.multi
    def mark_bank_reconciled(self):
        """
        If all payments in a batch deposit are marked as reconciled
        Then Batch deposit is reconciled automatically
        """
        for record in self:
            record._bank_reconcile(reconciled=True)

    @api.multi
    def undo_bank_reconciled(self):
        for record in self:
            record._bank_reconcile()

    def _bank_reconcile(self, reconciled=False):
        state = 'reconciled' if reconciled else 'draft'

        # mark payments + payments' aml as reconciled
        payment_ids = self.mapped('payment_ids')
        aml_ids = payment_ids.mapped('move_line_ids')
        aml_ids.write({'bank_reconciled': reconciled})
        payment_ids.write({'state': 'reconciled' if reconciled else 'posted'})

        # mark adjustment lines as reconciled
        fund_ids = self.mapped('fund_line_ids')
        fund_aml_ids = fund_ids.mapped('account_move_id').mapped('line_ids')
        fund_aml_ids.write({'bank_reconciled': reconciled})

        self.write({'state': state})

    @api.multi
    def _delete_fund_lines(self):
        """
        We have to call unlink of fund line manually to delete journal entry
        """
        self.mapped('fund_line_ids').unlink()

    @api.one
    @api.depends('payment_ids', 'journal_id', 'fund_line_ids')
    def _compute_amount(self):
        """
        Call super to calculate the total of all payment lines.
        Then add the total of fund lines.
        """
        super(AccountBatchDepositUSA, self)._compute_amount()

        company_currency = self.journal_id.company_id.currency_id or self.env.user.company_id.currency_id
        journal_currency = self.journal_id.currency_id or company_currency
        amount = 0
        for line in self.fund_line_ids:
            line_currency = line.currency_id or company_currency
            if line_currency == journal_currency:
                amount += line.amount
            else:
                # Note : this makes self.date the value date, which IRL probably is the date of the reception by the bank
                amount += line_currency.with_context({'date': self.payment_date}).compute(line.amount, journal_currency)

        self.amount += amount

    @api.multi
    def open_fund_entries(self):
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.fund_line_ids.mapped('account_move_id').ids)],
        }

    @api.model
    def create(self, values):
        result = super(AccountBatchDepositUSA, self).create(values)
        self._enable_trigger_find_possible_match(result)
        return result

    @api.multi
    def write(self, vals):
        res = super(AccountBatchDepositUSA, self).write(vals)
        self._enable_trigger_find_possible_match()
        return res

    @api.multi
    def unlink(self):
        # If we delete the batch deposits,
        # we must delete the bank statement line mapping manually to call computed fields
        self.env[ACCOUNT_BANK_STATEMENT_LINE_MAPPING].search([('batch_deposit_id', 'in', self.ids)]).sudo().unlink()

        # unmark reconciled status for payments & amls
        reconciled_batch_ids = self.filtered(lambda x: x.state == 'reconciled')
        reconciled_batch_ids.undo_bank_reconciled()

        self._delete_fund_lines()

        self._enable_trigger_find_possible_match()

        return super(AccountBatchDepositUSA, self).unlink()

    def _enable_trigger_find_possible_match(self, new_record=None):
        if new_record:
            journal_name = new_record.journal_id.name
            self.trigger_apply_matching(self.build_batch_deposit_key(journal_name))
            self.trigger_apply_matching(self.build_journal_item_key(journal_name))

        else:
            tracking = set()
            for record in self:
                journal_name = record.journal_id.name
                if journal_name in tracking:
                    continue

                self.trigger_apply_matching(self.build_batch_deposit_key(journal_name))
                self.trigger_apply_matching(self.build_journal_item_key(journal_name))

                tracking.add(journal_name)


class BatchDepositFundLine(models.Model):
    _name = 'account.batch.deposit.fund.line'
    _description = 'Batch Payment Fund Line'

    partner_id = fields.Many2one('res.partner', 'Customer')
    account_id = fields.Many2one('account.account', 'Account')
    communication = fields.Char('Description')
    payment_date = fields.Date('Date')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id)
    amount = fields.Monetary('Amount')
    account_move_id = fields.Many2one('account.move')
    batch_deposit_id = fields.Many2one('account.batch.payment', ondelete="cascade")

    def _get_account_side(self, journal_id, amount):
        debit_account = journal_id.default_debit_account_id if amount >= 0 else self.account_id
        credit_account = self.account_id if amount >= 0 else journal_id.default_credit_account_id

        return debit_account, credit_account

    def _create_account_move(self):
        # create journal entry
        journal_id = self.batch_deposit_id.journal_id
        reference_text = self.communication or self.batch_deposit_id.display_name + ' Adjustment'

        debit_account, credit_account = self._get_account_side(journal_id, self.amount)

        new_account_move = self.env['account.move'].create({
            'journal_id': journal_id.id,
            'line_ids': [(0, 0, {
                'partner_id': self.partner_id.id if self.partner_id else False,
                'account_id': debit_account.id,
                'debit': abs(self.amount),
                'credit': 0,
                'date': self.payment_date,
                'name': reference_text,
                'is_fund_line': True,
            }), (0, 0, {
                'partner_id': self.partner_id.id if self.partner_id else False,
                'account_id': credit_account.id,
                'debit': 0,
                'credit': abs(self.amount),
                'date': self.payment_date,
                'name': reference_text,
                'is_fund_line': True,
            })],
            'date': self.payment_date,
            'ref': reference_text,
        })
        self.account_move_id = new_account_move
        new_account_move.post()

    @api.onchange('payment_date', 'partner_id', 'account_id', 'communication', 'amount')
    def _onchange_validation(self):
        for record in self:
            if record.account_move_id:
                raise ValidationError(_('A journal entry has been created for this line. '
                                        'If you want to update anything, '
                                        'please delete this line and create a new one instead.'))

    @api.model
    def create(self, vals):
        res = super(BatchDepositFundLine, self).create(vals)
        res._create_account_move()
        return res

    @api.multi
    def unlink(self):
        for record in self:
            account_move_id = record.account_move_id
            if account_move_id:
                account_move_id.with_context(
                    {'journal_name_for_caching': account_move_id.journal_id.name}).button_cancel()
                account_move_id.unlink()
        return super(BatchDepositFundLine, self).unlink()
