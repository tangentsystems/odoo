# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.
from odoo import models
from ..models.model_const import (
    IR_CONFIG_PARAMETER,
    BATCH_DEPOSIT_APPLY_CACHING,
    JOURNAL_ITEM_APPLY_CACHING,
    BANK_STATEMENT_LINE_APPLY_CACHING,
    BANK_RULE_APPLY_CACHING,
)


class AccountCachingMixinUSA(models.AbstractModel):
    _name = 'account.caching.mixin.usa'
    _description = 'Caching Mixin'

    def trigger_apply_matching(self, param):
        config = self.env[IR_CONFIG_PARAMETER].sudo()
        if config.get_param(param) in ['False', False]:
            config.set_param(param, True)

    def is_apply_process(self, value):
        return self.env[IR_CONFIG_PARAMETER].sudo().get_param(value) == 'True'

    def enable_caching(self, value):
        self.env[IR_CONFIG_PARAMETER].sudo().set_param(value, 'False')

    @staticmethod
    def build_batch_deposit_key(journal_name):
        return '_'.join((BATCH_DEPOSIT_APPLY_CACHING, journal_name))

    @staticmethod
    def build_journal_item_key(journal_name):
        return '_'.join((JOURNAL_ITEM_APPLY_CACHING, journal_name))

    @staticmethod
    def build_bank_statement_line_key(journal_name):
        return '_'.join((BANK_STATEMENT_LINE_APPLY_CACHING, journal_name))

    @staticmethod
    def build_bank_rule_key(journal_name):
        return '_'.join((BANK_RULE_APPLY_CACHING, journal_name))

    def _trigger_apply_matching_journal(self, journal_name, tracking=set()):
        def _trigger(self, journal_name, tracking):
            if journal_name not in tracking:
                self.trigger_apply_matching(self.build_batch_deposit_key(journal_name))
                self.trigger_apply_matching(self.build_journal_item_key(journal_name))
                tracking.add(journal_name)
            return tracking

        tracking = tracking or set()
        _trigger(self, journal_name, tracking)

        if self:
            account_ids = []
            if self._name == 'account.move' and self.line_ids:
                account_ids = self.line_ids.mapped('account_id').ids
            elif self._name == 'account.move.line':
                account_ids = self.mapped('account_id').ids

            journal_ids = self.env['account.journal'].search(['|', ('default_debit_account_id', 'in', account_ids),
                                                              ('default_credit_account_id', 'in', account_ids)])
            for journal in journal_ids:
                _trigger(self, journal.name, tracking)
        return tracking
