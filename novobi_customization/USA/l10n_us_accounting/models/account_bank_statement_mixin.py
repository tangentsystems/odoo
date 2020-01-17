# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountBankStatementLineMatchingMixin(models.AbstractModel):
    _name = 'account.bank.statement.line.matching.mixin'
    _description = 'Bank Statement Line Matching Mixin'

    name = fields.Char(string='Number', compute='_compute_name', readonly=True, store=True, index=True)
    date = fields.Date(compute='_compute_date', index=True, readonly=True, store=True)
    partner_id = fields.Many2one('res.partner', string='Payee', ondelete='set null', compute='_compute_partner_id',
                                 readonly=True, store=True)
    journal_currency_id = fields.Many2one(related='mapping_id.journal_currency_id', readonly=True, store=True)
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total_amount', readonly=True, store=True,
                                   currency_field='journal_currency_id')

    journal_entry_id = fields.Many2one('account.move.line', string='Journal Item', readonly=True, ondelete='cascade',
                                       copy=False, auto_join=True, help='Link to the possible match with Journal Item.')

    batch_deposit_id = fields.Many2one('account.batch.payment', string='Batch Deposit', readonly=True,
                                       ondelete='cascade', copy=False, auto_join=True,
                                       help='Link to the possible match with Batch Deposit.')

    mapping_id = fields.Many2one('account.bank.statement.line', string='Bank Statement Line Mapping',
                                 ondelete='cascade', index=True, auto_join=True, readonly=True,
                                 help='The mapping result between bank statement line with journal item '
                                      'or batch deposit.')

    @api.multi
    @api.depends('journal_entry_id', 'batch_deposit_id')
    def _compute_name(self):
        for record in self:
            record.name = record.journal_entry_id.move_id.name if record.journal_entry_id else record.batch_deposit_id.name

    @api.multi
    @api.depends('journal_entry_id', 'journal_entry_id.date', 'batch_deposit_id', 'batch_deposit_id.date')
    def _compute_date(self):
        for record in self:
            record.date = record.journal_entry_id.date if record.journal_entry_id else record.batch_deposit_id.date

    @api.multi
    @api.depends('journal_entry_id')
    def _compute_partner_id(self):
        for record in self:
            if record.journal_entry_id:
                record.partner_id = record.journal_entry_id.partner_id

    @api.multi
    @api.depends('journal_entry_id', 'batch_deposit_id')
    def _compute_total_amount(self):
        for record in self:
            if record.journal_entry_id:
                record.total_amount = abs(record.journal_entry_id.balance)
            else:
                record.total_amount = record.batch_deposit_id.amount
