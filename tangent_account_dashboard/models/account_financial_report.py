# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo.addons.account_reports.models.account_financial_report import ReportAccountFinancialReport
from odoo import api, fields, models


class TangentReportAccountFinancialReport(models.Model):
    _inherit = 'account.financial.html.report.line'

    def _get_balance(self, linesDict, currency_table, financial_report, field_names=None):
        res = super(TangentReportAccountFinancialReport, self)._get_balance(linesDict, currency_table,
                                                                            financial_report, field_names)

        for rec in self:
            if rec.figure_type == 'percents':
                res[0]['balance'] *= 100

        return res

    def _format(self, value):
        if self.env.context.get('no_format'):
            return value
        value['no_format_name'] = value['name']
        if self.figure_type == 'percents':
            value['name'] = str(round(value['name'], 1)) + '%'
            return value
        else:
            return super(TangentReportAccountFinancialReport, self)._format(value)
