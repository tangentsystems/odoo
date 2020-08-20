# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import json
import ast
from odoo.osv import expression
from datetime import datetime, date
import calendar

from odoo.addons.account_dashboard.utils.utils import get_list_companies_child, format_currency
from odoo.addons.account_dashboard.utils.time_utils import get_list_period_by_type, BY_DAY, BY_WEEK, BY_MONTH, BY_QUARTER, BY_YEAR, BY_FISCAL_YEAR
from odoo.addons.account_dashboard.utils.graph_utils import get_json_render, get_json_data_for_selection, get_data_for_graph, append_data_fetch_to_list
from odoo.addons.l10n_custom_dashboard.utils.graph_setting import get_chartjs_setting, get_linechart_format, get_barchart_format, get_info_data, get_chart_json
import re
from decimal import Decimal
from dateutil.relativedelta import relativedelta

COLOR_INC = '#489e26'  # Green
COLOR_EXP = '#8e7cc3'  # Purple
COLOR_COS = '#cf2a27'  # Magenta
COLOR_DEP = '#fd7e14'
COLOR_OEX = '#f7cd1f'  # Yellow
COLOR_RATIO_PAST = "#2a78e4"
COLOR_RATIO_FUTURE = "#489e26"

CURRENT_RATIO = 'current_ratio'
RETURN_ON_EQUITY = 'return_on_equity'
DEBT_TO_EQUITY = 'debt_to_equity'
AR_TURNOVER = 'ar_turnover'
AP_TURNOVER = 'ap_turnover'
OP_CASHFLOW = 'op_cashflow'

USA_JOURNAL_TYPES = [
    (CURRENT_RATIO, 'Current Ratio'),
    (RETURN_ON_EQUITY, 'Return on Equity'),
    (DEBT_TO_EQUITY, 'Debt to Equity'),
    (AR_TURNOVER, 'AR Turnover'),
    (AP_TURNOVER, 'AP Turnover'),
    (OP_CASHFLOW, 'Operating Cash Flow')
]


class TangentUSAJournal(models.Model):
    _inherit = 'usa.journal'

    type = fields.Selection(selection_add=USA_JOURNAL_TYPES)

    @api.model
    def create_journal_data(self):
        usa_journal = self.env['usa.journal']
        types = [item[0] for item in USA_JOURNAL_TYPES]
        dict_elem = dict(USA_JOURNAL_TYPES)

        for com in self.env['res.company'].search([]):
            for journal_type in types:
                existing_journals = usa_journal.search([('type', '=', journal_type), ('company_id', '=', com.id)])
                if not existing_journals:
                    usa_journal.create({
                        'type': journal_type,
                        'name': dict_elem[journal_type],
                        'code': journal_type.upper(),
                        'company_id': com.id
                    })


    @api.depends()
    def compute_account_dashboard_graph(self):
        super(TangentUSAJournal, self).compute_account_dashboard_graph()

        for record in self:
            graph_data = None
            type_data = None
            extend_mode = None
            selection = []
            extra_param = []

            if record.type == CURRENT_RATIO:
                type_data = 'line'
                extend_mode, graph_data = record.get_general_kanban_section_data()
                function_retrieve = 'retrieve_current_ratio'
                get_json_data_for_selection(record, selection, record.period_by_complex, record.default_period_complex)

            if record.type == RETURN_ON_EQUITY:
                type_data = 'line'
                extend_mode, graph_data = record.get_general_kanban_section_data()
                function_retrieve = 'retrieve_return_on_equity'
                get_json_data_for_selection(record, selection, record.period_by_complex, record.default_period_complex)

            if record.type == DEBT_TO_EQUITY:
                type_data = 'line'
                extend_mode, graph_data = record.get_general_kanban_section_data()
                function_retrieve = 'retrieve_debt_to_equity'
                get_json_data_for_selection(record, selection, record.period_by_complex, record.default_period_complex)

            if record.type == AR_TURNOVER:
                type_data = 'line'
                extend_mode, graph_data = record.get_general_kanban_section_data()
                function_retrieve = 'retrieve_ar_turnover'
                get_json_data_for_selection(record, selection, record.period_by_complex, record.default_period_complex)

            if record.type == AP_TURNOVER:
                type_data = 'line'
                extend_mode, graph_data = record.get_general_kanban_section_data()
                function_retrieve = 'retrieve_ap_turnover'
                get_json_data_for_selection(record, selection, record.period_by_complex, record.default_period_complex)

            if record.type == OP_CASHFLOW:
                type_data = 'line'
                extend_mode, graph_data = record.get_general_kanban_section_data()
                function_retrieve = 'retrieve_op_cashflow'
                get_json_data_for_selection(record, selection, record.period_by_complex, record.default_period_complex)

            if graph_data:
                record.account_dashboard_graph_dashboard_graph = json.dumps(
                    get_json_render(type_data, False, '', graph_data, record.type, selection, function_retrieve, extra_param))
                record.extend_data = extend_mode

            if record.type != 'cash_forecast':
                today = date.today()
                end_of_current_month_day = calendar.monthrange(today.year, today.month)[1]
                end_of_current_month = date(today.year, today.month, end_of_current_month_day)
                last_11_months = end_of_current_month - relativedelta(months=11)
                start_of_last_12_months = date(last_11_months.year, last_11_months.month, 1)
                dashboard_data = json.loads(record.account_dashboard_graph_dashboard_graph)
                dashboard_data[0]['selection'].append({
                    'n': 'Last 12 Months',
                    's': fields.Date.to_string(start_of_last_12_months),
                    'e': fields.Date.to_string(end_of_current_month),
                    'd': True,
                    'k': 'month'
                })
                record.account_dashboard_graph_dashboard_graph = json.dumps(dashboard_data)

    def open_action_label(self):
        self.ensure_one()
        action_name = self._context.get('action_name', False)
        action = None
        if not action_name:
            if self.type == CURRENT_RATIO or self.type == RETURN_ON_EQUITY \
                    or self.type == AR_TURNOVER or self.type == AP_TURNOVER:
                action = self.env.ref('account_reports.account_financial_report_executivesummary0') \
                    .generated_menu_id \
                    .action
                action_name = action.xml_id
                [action] = self.env.ref(action_name).read()
            if self.type == DEBT_TO_EQUITY:
                action = self.env.ref('account_reports.account_financial_report_balancesheet0') \
                    .generated_menu_id \
                    .action
                action_name = action.xml_id
                [action] = self.env.ref(action_name).read()

            if self.type == OP_CASHFLOW:
                action = self.env.ref('account_reports.action_account_report_cs')
                action_name = action.xml_id
                [action] = self.env.ref(action_name).read()

        else:
            action = super(TangentUSAJournal, self).open_action_label()

        return action

    @api.model
    def retrieve_current_ratio(self, date_from, date_to, period_type):
        info_data = []
        data_fetch = []
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        periods = get_list_period_by_type(self, date_from, date_to, period_type)

        financial_report = self.env.ref('account_reports.account_financial_report_executivesummary0')
        financial_line = self.env.ref('account_reports.account_financial_report_executivesummary_ca_to_l0')

        # Formula: Current assets / Current liabilities
        # Using Current assets to liabilities value in Executive Summary report
        # Get ratio based on start date and end date
        ca_to_l0 = self._get_financial_report_line_values(date_from, date_to, financial_report, financial_line)[0]
        info_data.append({
            'name': 'Current assets to liabilities',
            'summarize': ca_to_l0['value']
        })

        # Get ratio based on periods
        for period in periods:
            ca_to_l0 = self._get_financial_report_line_values(period[0], period[1], financial_report, financial_line)[0]

            if ca_to_l0['value']:
                data_fetch.append({
                    'year': period[0].year,
                    'date_in_period': period[0],
                    'value': ca_to_l0['value']
                })

        graph_label = []
        graph_data = self._prepare_line_chart_data('Ratio', data_fetch, periods, period_type, graph_label)
        json_data = get_chart_json(graph_data, graph_label, get_chartjs_setting(chart_type='line'), info_data)
        json_data['setting'].update(no_currency=True)

        return json_data

    @api.model
    def retrieve_return_on_equity(self, date_from, date_to, period_type):
        info_data = []
        data_fetch = []
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        periods = get_list_period_by_type(self, date_from, date_to, period_type)

        financial_report = self.env.ref('account_reports.account_financial_report_executivesummary0')
        net_profit_line = self.env.ref('account_reports.account_financial_report_executivesummary_profit0')
        net_assets_line = self.env.ref('account_reports.account_financial_report_executivesummary_net_assets0')

        # Formula: Net Income / Shareholder Equity
        # Get ratio based on start date and end date
        net_profit = self._get_financial_report_line_values(date_from, date_to, financial_report, net_profit_line)[0]
        net_assets = self._get_financial_report_line_values(date_from, date_to, financial_report, net_assets_line)[0]
        if net_assets['no_format_value']:
            ratio = net_profit['no_format_value'] / net_assets['no_format_value']
            info_data.append({
                'name': 'Return on Equity',
                'summarize': round(ratio, 2)
            })

        # Get ratio based on periods
        for period in periods:
            net_profit = self._get_financial_report_line_values(period[0], period[1],
                                                                financial_report, net_profit_line)[0]
            net_assets = self._get_financial_report_line_values(period[0], period[1],
                                                                financial_report, net_assets_line)[0]

            ratio = net_profit['no_format_value'] / net_assets['no_format_value'] if net_assets['no_format_value'] else 0

            data_fetch.append({
                'year': period[0].year,
                'date_in_period': period[0],
                'value': round(ratio, 2)
            })

        graph_label = []
        graph_data = self._prepare_line_chart_data('Return on Equity', data_fetch, periods, period_type, graph_label)
        json_data = get_chart_json(graph_data, graph_label, get_chartjs_setting(chart_type='line'), info_data)
        json_data['setting'].update(no_currency=True)

        return json_data

    @api.model
    def retrieve_debt_to_equity(self, date_from, date_to, period_type):
        info_data = []
        data_fetch = []
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        periods = get_list_period_by_type(self, date_from, date_to, period_type)

        financial_report = self.env.ref('account_reports.account_financial_report_balancesheet0')
        liabilities_line = self.env.ref('account_reports.account_financial_report_liabilities_view0')
        equity_line = self.env.ref('account_reports.account_financial_report_equity0')

        # Formula: Total Liabilities / Total Shareholder's Equity
        # Get ratio based on start date and end date
        liabilities = self._get_financial_report_line_values(date_from, date_to, financial_report, liabilities_line)
        equity = self._get_financial_report_line_values(date_from, date_to, financial_report, equity_line)

        liabilities = list(filter(lambda e: e['id'] == liabilities_line.id and e['value'], liabilities))[0]
        equity = list(filter(lambda e: e['id'] == equity_line.id and e['value'], equity))[0]

        if equity['no_format_value']:
            ratio = liabilities['no_format_value'] / equity['no_format_value']
            info_data.append({
                'name': 'Debt to Equity',
                'summarize': round(ratio, 2)
            })

        # Get ratio based on periods
        for period in periods:
            liabilities = self._get_financial_report_line_values(period[0], period[1],
                                                                 financial_report, liabilities_line)
            equity = self._get_financial_report_line_values(period[0], period[1],
                                                            financial_report, equity_line)
            liabilities = list(filter(lambda e: e['id'] == liabilities_line.id and e['value'], liabilities))[0]
            equity = list(filter(lambda e: e['id'] == equity_line.id and e['value'], equity))[0]

            ratio = liabilities['no_format_value'] / equity['no_format_value'] if equity['no_format_value'] else 0

            data_fetch.append({
                'year': period[0].year,
                'date_in_period': period[0],
                'value': round(ratio, 2)
            })

        graph_label = []
        graph_data = self._prepare_line_chart_data('Debt to Equity', data_fetch, periods, period_type, graph_label)
        json_data = get_chart_json(graph_data, graph_label, get_chartjs_setting(chart_type='line'), info_data)
        json_data['setting'].update(no_currency=True)

        return json_data

    @api.model
    def retrieve_ar_turnover(self, date_from, date_to, period_type):
        financial_report = self.env.ref('account_reports.account_financial_report_executivesummary0')
        receivables_line = self.env.ref('account_reports.account_financial_report_executivesummary_debtors0')

        graph_data = self._get_turn_over_data(financial_report, receivables_line, 'AR Turnover', date_from,
                                              date_to, period_type, 'out_invoice', 'out_refund')

        return graph_data

    @api.model
    def retrieve_ap_turnover(self, date_from, date_to, period_type):
        financial_report = self.env.ref('account_reports.account_financial_report_executivesummary0')
        payables_line = self.env.ref('account_reports.account_financial_report_executivesummary_creditors0')

        graph_data = self._get_turn_over_data(financial_report, payables_line, 'AP Turnover', date_from,
                                              date_to, period_type, 'in_invoice', 'in_refund')

        return graph_data

    @api.model
    def retrieve_op_cashflow(self, date_from, date_to, period_type):
        info_data = []
        data_fetch = []
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        periods = get_list_period_by_type(self, date_from, date_to, period_type)

        date = {
            'date_from': date_from,
            'date_to': date_to,
            'filter': 'custom'
        }
        options = {
            'date': date,
            'unfolded_lines': []
        }

        cashflow_lines = self.env['account.cash.flow.report']._get_lines(options)
        op_cashflow = list(filter(lambda e: e['id'] == 'cash_flow_line_2', cashflow_lines))[0]
        info_data.append({
            'name': 'Operating Cash Flow',
            'summarize': op_cashflow['columns'][0]['name']
        })

        for period in periods:
            options['date']['date_from'] = period[0]
            options['date']['date_to'] = period[1]
            cashflow_lines = self.env['account.cash.flow.report']._get_lines(options)
            op_cashflow = list(filter(lambda e: e['id'] == 'cash_flow_line_2', cashflow_lines))[0]
            value = float(re.sub(r'[^\d.-]', '', op_cashflow['columns'][0]['name']))

            data_fetch.append({
                'year': period[0].year,
                'date_in_period': period[0],
                'value': value
            })

        graph_label = []
        graph_data = self._prepare_line_chart_data('Operating Cash Flow', data_fetch, periods, period_type, graph_label)
        json_data = get_chart_json(graph_data, graph_label, get_chartjs_setting(chart_type='line'), info_data)

        return json_data

    @api.model
    def _get_turn_over_data(self, report, report_line, chart_label, date_from, date_to, period_type,
                            invoice_type, refund_type):
        info_data = []
        data_fetch = []
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        periods = get_list_period_by_type(self, date_from, date_to, period_type)

        # AR Turnover
        # Formula: Net Credit Sales / Average Accounts Receivable During Period
        # Average Accounts Receivable  = (AR at end of period + AR at beginning of period)/2

        # AP Turnover
        # Formula: Total Supply Purchases / Average Accounts Payable During Period
        # Average Accounts Payable = (AP at end of period + AP at beginning of period)/2

        # Get average account receivable and net credit sales based on date range
        ar_ap_start = self._get_financial_report_line_values(date_from, date_from, report, report_line)[0]
        ar_ap_end = self._get_financial_report_line_values(date_to, date_to, report, report_line)[0]

        invoice_values = self._get_invoices_value(date_from, date_to, period_type, invoice_type)
        refund_values = self._get_invoices_value(date_from, date_to, period_type, refund_type)
        sum_of_invoices = sum(item['amount_untaxed'] for item in invoice_values)
        sum_of_refunds = sum(item['amount_untaxed'] for item in refund_values)
        net_value = sum_of_invoices - sum_of_refunds

        average_ar_ap = (ar_ap_start['no_format_value'] + ar_ap_end['no_format_value']) / 2
        if average_ar_ap:
            ratio = net_value / abs(average_ar_ap)
            info_data.append({
                'name': chart_label,
                'summarize': round(ratio, 2)
            })

        # Get data based on periods
        for period in periods:
            ar_ap_start = self._get_financial_report_line_values(period[0], period[0], report, report_line)[0]
            ar_ap_end = self._get_financial_report_line_values(period[1], period[1], report, report_line)[0]
            average_ar_ap = (ar_ap_start['no_format_value'] + ar_ap_end['no_format_value']) / 2

            invoice_in_period = list(filter(lambda e: period[0] <= e['date_in_period'] <= period[1], invoice_values))
            refund_in_period = list(filter(lambda e: period[0] <= e['date_in_period'] <= period[1], refund_values))
            sum_of_invoices = invoice_in_period[0]['amount_untaxed'] if invoice_in_period else 0
            sum_of_refunds = refund_in_period[0]['amount_untaxed'] if refund_in_period else 0
            net_value = sum_of_invoices - sum_of_refunds

            ratio = net_value / abs(average_ar_ap) if average_ar_ap else 0
            data_fetch.append({
                'year': period[0].year,
                'date_in_period': period[0],
                'value': round(ratio, 2)
            })

        graph_label = []
        graph_data = self._prepare_line_chart_data(chart_label, data_fetch, periods, period_type, graph_label)
        json_data = get_chart_json(graph_data, graph_label, get_chartjs_setting(chart_type='line'), info_data)
        json_data['setting'].update(no_currency=True)

        return json_data

    @api.model
    def _get_invoices_value(self, date_from, date_to, period_type, invoice_type):
        currency = """  SELECT c.id,
                            COALESCE((SELECT r.rate
                                        FROM res_currency_rate r
                                        WHERE r.currency_id = c.id AND r.name <= %s
                                            AND (r.company_id IS NULL OR r.company_id IN %s)
                                        ORDER BY r.company_id, r.name DESC LIMIT 1), 1.0) AS rate
                        FROM res_currency c"""

        transferred_currency = """select ai.invoice_date, ai.type, c.rate * ai.amount_untaxed as amount_tran, state, company_id
                                    from account_move as ai
                                        left join ({currency_table}) as c
                                        on ai.currency_id = c.id""".format(currency_table=currency, )

        query = """ SELECT date_part('year', aic.invoice_date::date) as year,
                                   date_part(%s, aic.invoice_date::date) AS period,
                                   MIN(aic.invoice_date) as date_in_period,
                                   SUM(aic.amount_tran) as amount_untaxed
                            FROM ({transferred_currency_table}) as aic
                            WHERE invoice_date >= %s AND
                                  invoice_date <= %s AND
                                  aic.state = 'posted' AND
                                  aic.type = '{invoice_type}' AND
                                  aic.company_id IN %s
                            GROUP BY year, period
                            ORDER BY year, period;""".format(transferred_currency_table=transferred_currency,
                                                             invoice_type=invoice_type)

        company_ids = get_list_companies_child(self.env.user.company_id)
        name = fields.Date.today()
        self.env.cr.execute(query, (period_type, name, tuple(company_ids), date_from, date_to, tuple(company_ids),))
        data_fetch = self.env.cr.dictfetchall()

        return data_fetch

    @api.model
    def _get_financial_report_line_values(self, date_from, date_to, report, line=None):
        date_range = {
            'date_from': fields.Date.to_string(date_from),
            'date_to': fields.Date.to_string(date_to),
            'filter': 'custom'
        }
        options = {
            'all_entries': False,
        }
        options.update(date=date_range)
        lines = report.with_context({'state': 'posted'})._get_lines(options, line.id if line else None)
        result = []
        for item in lines:
            if item['columns'][0].get('no_format_name', False):
                no_format_value = float(item['columns'][0]['no_format_name'])
            else:
                no_format_value = 0
            result.append({
                'id': item['id'],
                'name': item['name'],
                'value': item['columns'][0]['name'],
                'no_format_value': no_format_value
            })

        return result

    @api.model
    def _prepare_line_chart_data(self, label, data_fetch, periods, period_type, graph_label):
        data_list = [[], []]
        index = 0
        total_value = 0

        today = date.today()
        for data in data_fetch:
            while not (periods[index][0] <= data['date_in_period'] <= periods[index][1]) and index < len(periods):
                values = [
                    0 if periods[index][0] <= today else 'NaN',
                    0 if periods[index][1] >= today else 'NaN'
                ]
                append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=values)
                index += 1

            if index < len(periods):
                value = data.get('value', False)
                values = [
                    value if not isinstance(value, bool) and periods[index][0] <= today else 'NaN',
                    value if not isinstance(value, bool) and periods[index][1] >= today else 'NaN'
                ]
                total_value += value if value else 0
                append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=values)
                index += 1

        while index < len(periods):
            values = [
                0 if periods[index][0] <= today else 'NaN',
                0 if periods[index][1] >= today else 'NaN'
            ]
            append_data_fetch_to_list(data_list, graph_label, periods, period_type, index, values=values)
            index += 1

        graph_data = [
            get_linechart_format(data=data_list[0], label=_(label), color=COLOR_RATIO_PAST),
            get_linechart_format(data=data_list[1], label=_('Future'), color=COLOR_RATIO_FUTURE),
        ]

        return graph_data

    @api.model
    def retrieve_profit_and_loss(self, date_from, date_to, period_type):
        data = super(TangentUSAJournal, self).retrieve_profit_and_loss(date_from, date_to, period_type)
        data['data'].pop()
        data['data'][0]['borderColor'] = COLOR_INC
        data['data'][0]['backgroundColor'] = COLOR_INC
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        expense_types = {
            'EXP': ('Operating Expense', COLOR_EXP),
            'COS': ('Cost of Revenue', COLOR_COS),
            'DEP': ('Depreciation', COLOR_DEP),
            'OEX': ('Other Expense', COLOR_OEX)
        }

        # Calculate operating income
        domain_group = self.env['account.financial.html.report.line'].search([('code', '=', 'OPINC')]).mapped(lambda g: ast.literal_eval(g.domain))
        domain = expression.OR(domain_group)
        group_data = self.env['account.move.line'].summarize_group_account(date_from, date_to, period_type, domain)
        total_opinc, opinc_values, labels = get_data_for_graph(self, date_from, date_to, period_type, group_data, ['total_balance'])

        # Calculate expenses
        total_cos = 0
        for key, value in expense_types.items():
            domain_group = self.env['account.financial.html.report.line'].search([('code', '=', key)]).mapped(lambda g: ast.literal_eval(g.domain))
            domain = expression.OR(domain_group)
            group_data = self.env['account.move.line'].summarize_group_account(date_from, date_to, period_type, domain)
            total_expense, expense_values, labels = get_data_for_graph(self, date_from, date_to, period_type, group_data, ['total_balance'])
            if key == 'COS':
                total_cos = total_expense[0]
            data['data'].append({
                'label': value[0],
                'data': expense_values[0],
                'backgroundColor': value[1],
                'borderColor': value[1]
            })

        data['info_data'].append({
            'name': 'Gross Margin',
            'summarize': format_currency(self, abs(total_opinc[0]) - abs(total_cos))
        })
        data['setting'].update(stack_group_bar=True)

        return data
