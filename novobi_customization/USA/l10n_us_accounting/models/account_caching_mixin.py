# -*- coding: utf-8 -*-
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
