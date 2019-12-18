# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMatchingBankStatementLine(models.TransientModel):
    """Account Matching Bank Statement Line"""

    _name = 'account.matching.bank.statement.line'
    _inherit = 'account.bank.statement.line.matching.mixin'
    _description = 'List all candidates that can be matched with a bank statement line'

    selected_item = fields.Boolean(string='Select')
