# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import random
import re
import ast

from ..utils.graph_utils import get_json_render, get_json_data_for_selection, push_to_list_lists_at_timestamp, \
    push_to_list_values_to_sales
from odoo import api, fields, models, _
from odoo.osv import expression

from datetime import datetime, date, timedelta

from ..utils.time_utils import get_list_period_by_type, \
    BY_DAY, BY_WEEK, BY_MONTH, BY_QUARTER, BY_YEAR, BY_FISCAL_YEAR, \
    get_start_end_date_value, get_start_end_date_value_with_delta, get_same_date_delta_period
from ..utils.utils import get_list_companies_child, format_currency

COLOR_VALIDATION_DATA = "#337ab7"
COLOR_INCOME = "#2b78e4"
COLOR_EXPENSE = "#cf2a27"
COLOR_SALE_PAST = "#2a78e4"
COLOR_SALE_FUTURE = "#489e26"
COLOR_CASH_OUT = "#f1c232"
COLOR_CASH_IN = "#00ffff"
COLOR_NET_CASH = "#2978e4"
COLOR_BANK = "#009e0f"
COLOR_BOOK = "#ff9900"
COLOR_OPEN_INVOICES = "#f3993e"
COLOR_PAID_INVOICE = "#2b78e4"
COLOR_OPEN_BILLS = "#8e7cc3"
COLOR_PAID_BILLS = "#6fa8dc"

PROFIT_LOT = 'profit_and_loss'
SALES = 'sales'
CASH = 'cash'
BANK = 'bank'
CUSTOMER_INVOICE = 'sale'
VENDOR_BILLS = 'purchase'


class USAJournal(models.Model):
    _name = "usa.journal"
    _description = "US Accounting journal"

    period_by_month = [{'n': 'This Month', 'd': 0, 't': BY_MONTH},
                       {'n': 'This Quarter', 'd': 0, 't': BY_QUARTER},
                       {'n': 'This Fiscal Year', 'd': 0, 't': BY_FISCAL_YEAR},
                       {'n': 'Last Month', 'd': -1, 't': BY_MONTH},
                       {'n': 'Last Quarter', 'd': -1, 't': BY_QUARTER},
                       {'n': 'Last Fiscal Year', 'd': -1, 't': BY_FISCAL_YEAR}, ]

    period_by_month_fiscal_year = [{'n': 'This Month', 'd': 0, 't': BY_MONTH, 'td': False},
                                   {'n': 'This Quarter', 'd': 0, 't': BY_QUARTER, 'td': False},
                                   {'n': 'This Year', 'd': 0, 't': BY_YEAR, 'td': False},
                                   {'n': 'Last Month', 'd': -1, 't': BY_MONTH, 'td': False},
                                   {'n': 'Last Quarter', 'd': -1, 't': BY_QUARTER, 'td': False},
                                   {'n': 'Last Fiscal Year', 'd': -1, 't': BY_YEAR, 'td': True}, ]

    period_by_complex = [{'n': 'This Week by Day', 'd': 0, 'k': BY_DAY, 't': BY_WEEK},
                         {'n': 'This Month by Week', 'd': 0, 'k': BY_WEEK, 't': BY_MONTH},
                         {'n': 'This Quarter by Month', 'd': 0, 'k': BY_MONTH, 't': BY_QUARTER},
                         {'n': 'This Fiscal Year by Month', 'd': 0, 'k': BY_MONTH, 't': BY_FISCAL_YEAR},
                         {'n': 'This Fiscal Year by Quarter', 'd': 0, 'k': BY_QUARTER, 't': BY_FISCAL_YEAR},
                         {'n': 'Last Week by Day', 'd': -1, 'k': BY_DAY, 't': BY_WEEK},
                         {'n': 'Last Month by Week', 'd': -1, 'k': BY_WEEK, 't': BY_MONTH},
                         {'n': 'Last Quarter by Month', 'd': -1, 'k': BY_MONTH, 't': BY_QUARTER},
                         {'n': 'Last Fiscal Year by Month', 'd': -1, 'k': BY_MONTH, 't': BY_FISCAL_YEAR},
                         {'n': 'Last Fiscal Year by Quarter', 'd': -1, 'k': BY_QUARTER, 't': BY_FISCAL_YEAR}, ]
    default_period_by_month = 'This Fiscal Year'
    default_period_complex = 'This Fiscal Year by Month'

    type_element = [
        (PROFIT_LOT, _('Profit and Loss')),
        (SALES, _('Sales')),
        (CASH, _('Cash')),
    ]

    code = fields.Char(string='Code', required=True)
    type = fields.Selection(type_element, required=True)
    name = fields.Char('Element Name', required=True)
    account_dashboard_graph_dashboard_graph = fields.Text(compute='compute_account_dashboard_graph', store=False)
    extend_data = fields.Boolean(compute='compute_account_dashboard_graph', default=False, store=True)
    show_on_dashboard = fields.Boolean(string='Show journal on dashboard',
                                       help="Whether this journal should be displayed on the dashboard or not",
                                       default=True)
    color = fields.Integer("Color Index", default=0)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
                                 default=lambda self: self.env.user.company_id,
                                 help="Company related to this journal")

    @api.one
    @api.depends()
    def compute_account_dashboard_graph(self):
        print("compute_account_dashboard_graph")
        graph_data = None
        type_data = None
        extend_mode = None
        function_retrieve = ""
        selection = []
        extra_param = []

        if self.type == PROFIT_LOT:
            type_data = "bar"
            _, graph_data = self.get_general_kanban_section_data()
            function_retrieve = 'retrieve_profit_and_loss'
            get_json_data_for_selection(self, selection, self.period_by_month, self.default_period_by_month)

        if self.type == SALES:
            type_data = "line"
            extend_mode, graph_data = self.get_general_kanban_section_data()
            function_retrieve = 'retrieve_sales'
            get_json_data_for_selection(self, selection, self.period_by_complex, self.default_period_complex)

        if self.type == CASH:
            type_data = "multi_chart"
            extend_mode, graph_data = self.get_general_kanban_section_data()
            function_retrieve = 'retrieve_cash'
            get_json_data_for_selection(self, selection, self.period_by_complex, self.default_period_complex)

        if self.type == BANK:
            type_data = "horizontal_bar"
            extend_mode, graph_data = self.get_bar_by_category_graph_data()

        if self.type == CUSTOMER_INVOICE:
            type_data = "bar"
            extend_mode, graph_data = self.get_general_kanban_section_data()
            function_retrieve = 'retrieve_account_invoice'
            get_json_data_for_selection(self, selection, self.period_by_month_fiscal_year, self.default_period_by_month)
            extra_param.append(self.type)

        if self.type == VENDOR_BILLS:
            type_data = "bar"
            extend_mode, graph_data = self.get_general_kanban_section_data()
            function_retrieve = 'retrieve_account_invoice'
            get_json_data_for_selection(self, selection, self.period_by_month_fiscal_year, self.default_period_by_month)
            extra_param.append(self.type)

        if graph_data:
            self.account_dashboard_graph_dashboard_graph = json.dumps(
                get_json_render(type_data, False,
                                graph_data, self.type,
                                selection, function_retrieve, extra_param))
            self.write({'extend_data': extend_mode})

    ########################################################
    # GENERAL FUNCTION
    ########################################################
    @api.multi
    def comp_ins_action(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Company Insight'),
            'res_model': 'usa.journal',
            'view_mode': 'kanban',
            'target': 'main',
        }
        return action

    def change_status_extend(self, extend):
        object_json = json.loads(self.account_dashboard_graph_dashboard_graph)
        object_json['extend'] = extend
        json_return = json.dumps(object_json)
        return json_return

    @api.multi
    def get_bar_by_category_graph_data(self):
        data = []

        for i in range(10):
            value = random.randint(1, 100)
            label = 'label ' + str(value)
            data.append({'label': label, 'value': value, 'type': label})
        data = sorted(data, key=lambda v: v.get('value'), reverse=True)

        (graph_title, graph_key) = ('', '')
        extend_data = True if (len(data) > 5) else False
        return extend_data, [{
            'values': data,
            'title': graph_title,
            'key': graph_key,
            'color': COLOR_VALIDATION_DATA}]

    @api.multi
    def get_general_kanban_section_data(self):
        data = []

        (graph_title, graph_key) = ('', '')
        extend_data = False
        return extend_data, [{
            'values': data,
            'title': graph_title,
            'key': graph_key,
            'color': COLOR_VALIDATION_DATA}]

    ########################################################
    # BUTTON EVENT
    ########################################################
    @api.multi
    def action_extend_view(self):
        """ Function implement action click button is named 'EXTEND' in
        each kanban section

        :return:
        """
        pass

    @api.multi
    def open_action_label(self):
        """ Function return action based on type for related journals

        :return:
        """
        action_name = self._context.get('action_name', False)
        domain = []
        action = None
        if not action_name:
            if self.type == PROFIT_LOT:
                action = self.env.ref('account_reports.account_financial_report_profitandloss0') \
                    .generated_menu_id \
                    .action
                action_name = action.xml_id
            elif self.type == SALES:
                action_name = 'account.action_invoice_tree1'
                domain = [('type', '=', 'out_invoice')]
            elif self.type == CASH:
                action = self.env.ref('account_reports.account_financial_report_cashsummary0') \
                    .generated_menu_id \
                    .action
                action_name = action.xml_id
            elif self.type == CUSTOMER_INVOICE:
                action_name = 'account.action_invoice_tree1'
                domain = [('type', '=', 'out_invoice')]
            elif self.type == VENDOR_BILLS:
                action_name = 'account.action_vendor_bill_template'
                domain = [('type', '=', 'in_invoice')]
            else:
                action_name = 'action_none'

        _journal_invoice_type_map = {
            (CUSTOMER_INVOICE, None): 'out_invoice',
            (SALES, None): 'out_invoice',
            (VENDOR_BILLS, None): 'in_invoice',
            (CUSTOMER_INVOICE, 'refund'): 'out_refund',
            (VENDOR_BILLS, 'refund'): 'in_refund',
            (BANK, None): BANK,
            (CASH, None): CASH,
            ('general', None): 'general',
        }
        if not action:
            journal_id = self.env['account.journal'].search([('type', '=', self.type)]).id
            invoice_type = _journal_invoice_type_map[(self.type, self._context.get('invoice_type'))]

            ctx = self._context.copy()
            ctx.pop('group_by', None)
            ctx.update({
                'journal_type': self.type,
                'default_journal_id': journal_id,
                'default_type': invoice_type,
                'type': invoice_type
            })
        else:
            ctx = action.context

        [action] = self.env.ref(action_name).read()

        # Copy and modify from file account_journal_dashboard.py
        if domain and self.type == VENDOR_BILLS:
            purchase_journal_id = self.env['account.journal'].search([('type', '=', 'purchase')]).id
            ctx['search_default_journal_id'] = purchase_journal_id

        action['context'] = ctx
        action['domain'] = domain

        # Copy and modify from file account_journal_dashboard.py
        account_invoice_filter = self.env.ref('account.view_account_invoice_filter', False)
        if self.type in [CUSTOMER_INVOICE, VENDOR_BILLS]:
            action['search_view_id'] = account_invoice_filter and account_invoice_filter.id or False

        if self.type == VENDOR_BILLS:
            new_help = self.env['account.invoice'].with_context(ctx).complete_empty_list_help()
            action.update({'help': action.get('help', '') + new_help})
        return action

    @api.multi
    def action_create_new(self):
        """ Function implement action click button New "X" in Vendor bills and customer invoices

        :return:
        """
        ctx = self._context.copy()
        model = 'account.invoice'
        if self.type == CUSTOMER_INVOICE:
            sale_id = self.env['account.journal'].search([('type', '=', 'sale')]).id
            ctx.update({
                'journal_type': self.type,
                'default_type': 'out_invoice',
                'type': 'out_invoice',
                'default_journal_id': sale_id})
            if ctx.get('refund'):
                ctx.update({'default_type': 'out_refund', 'type': 'out_refund'})
            view_id = self.env.ref('account.invoice_form').id
        elif self.type == VENDOR_BILLS:
            purchase_id = self.env['account.journal'].search([('type', '=', 'purchase')]).id
            ctx.update({'journal_type': self.type,
                        'default_type': 'in_invoice',
                        'type': 'in_invoice',
                        'default_journal_id': purchase_id})
            if ctx.get('refund'):
                ctx.update({'default_type': 'in_refund', 'type': 'in_refund'})
            view_id = self.env.ref('account.invoice_supplier_form').id

        else:
            ctx.update({'default_journal_id': self.id, 'view_no_maturity': True})
            view_id = self.env.ref('account.view_move_form').id
            model = 'account.move'
        return {
            'name': _('Create invoice/bill'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': model,
            'view_id': view_id,
            'context': ctx,
        }

    @api.multi
    def open_action(self):
        """return action based on type for related journals"""
        action_name = self._context.get('action_name', False)
        if not action_name:
            if self.type == BANK:
                action_name = 'action_bank_statement_tree'
            elif self.type == CUSTOMER_INVOICE:
                action_name = 'action_invoice_tree1'
                self = self.with_context(use_domain=[('type', '=', 'out_invoice')])
            elif self.type == VENDOR_BILLS:
                action_name = 'action_vendor_bill_template'
                self = self.with_context(use_domain=[('type', '=', 'in_invoice')])
            else:
                action_name = 'action_move_journal_line'

        _journal_invoice_type_map = {
            (CUSTOMER_INVOICE, None): 'out_invoice',
            (VENDOR_BILLS, None): 'in_invoice',
            (CUSTOMER_INVOICE, 'refund'): 'out_refund',
            (VENDOR_BILLS, 'refund'): 'in_refund',
            (BANK, None): BANK,
            (CASH, None): CASH,
            ('general', None): 'general',
        }
        invoice_type = _journal_invoice_type_map[(self.type, self._context.get('invoice_type'))]

        ctx = self._context.copy()
        ctx.pop('group_by', None)
        ctx.update({
            'journal_type': self.type,
            'default_journal_id': self.id,
            'default_type': invoice_type,
            'type': invoice_type
        })

        [action] = self.env.ref('account.%s' % action_name).read()
        if not self.env.context.get('use_domain'):
            ctx['search_default_journal_id'] = self.id
        action['context'] = ctx
        action['domain'] = self._context.get('use_domain', [])
        account_invoice_filter = self.env.ref('account.view_account_invoice_filter', False)
        if action_name in ['action_invoice_tree1', 'action_vendor_bill_template']:
            action['search_view_id'] = account_invoice_filter and account_invoice_filter.id or False
        if action_name in ['action_bank_statement_tree', 'action_view_bank_statement_tree']:
            action['views'] = False
            action['view_id'] = False
        if self.type == VENDOR_BILLS:
            new_help = self.env['account.invoice'].with_context(ctx).complete_empty_list_help()
            action.update({'help': action.get('help', '') + new_help})
        return action

    @api.multi
    def action_open_reconcile(self):
        if self.type in [BANK]:
            # Open reconciliation view for bank statements belonging to this journal
            bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)])
            return {
                'type': 'ir.actions.client',
                'tag': 'bank_statement_reconciliation_view',
                'context': {
                    'statement_ids': bank_stmt.ids,
                    'company_ids': self.mapped('company_id').ids
                },
            }
        else:
            # Open reconciliation view for customers/suppliers
            action_context = {
                'show_mode_selector': False,
                'company_ids': self.env.user.company_id
            }
            if self.type == CUSTOMER_INVOICE:
                action_context.update({'mode': 'customers'})
            elif self.type == VENDOR_BILLS:
                action_context.update({'mode': 'suppliers'})
            return {
                'type': 'ir.actions.client',
                'tag': 'manual_reconciliation_view',
                'context': action_context,
            }

    ########################################################
    # INITIAL DATA
    ########################################################
    @api.model
    def init_data_usa_journal(self):
        print("init_data_usa_journal")
        usa_journal = self.env['usa.journal']
        types = [item[0] for item in self.type_element]
        dict_elem = dict(self.type_element)
        for journal_type in types:
            if journal_type != BANK:
                for com in self.env['res.company'].search([]):
                    usa_journal.create({
                        'type': journal_type,
                        'name': dict_elem[journal_type],
                        'code': journal_type.upper(),
                        'company_id': com.id
                    })
            else:
                # Append all the bank journal are exist to the usa journal
                banks = self.env['account.journal'].search([('type', '=', 'bank')])
                for bank in banks:
                    usa_journal.create({
                        'type': journal_type,
                        'name': bank.name,
                        'code': bank.code.upper() + str(bank.id),
                        'company_id': bank.company_id.id
                    })

    ########################################################
    # API
    ########################################################
    @api.model
    def retrieve_profit_and_loss(self, date_from, date_to, period_type=BY_MONTH):
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')

        # Profit and loss record in account reports
        pal = self.env.ref('account_reports.account_financial_report_profitandloss0')

        # Net Income record in account reports
        ni = self.env.ref('account_reports.account_financial_report_net_profit0')
        list_lines = pal.mapped('line_ids')

        # create the tree of formula to compute each group
        demo = list(list_lines)
        dict_journal_item = {}

        # Loop in the queue of report line saved in demo variable
        while len(demo):
            # pop at the head of queue
            line = demo.pop(0)
            dict_journal_item.setdefault(line.code, {'pos': 1, 'child': [], 'code': line.code})

            # push all childes of report line have get from the variable 'line' at tail of queue
            demo += list(line.children_ids)
            # Remove the tail (.xxx) of code variable and space.
            # The formula variable contain the formula is used to compute for variable before the equal symbol
            formula = re.sub(r'\.\w+', '', line.formulas.replace(' ', '')).split('=')[1]

            # Var 'codes' is a list containing all parameter in the formula
            codes = re.split("\W", formula)
            for code in codes:
                if code:
                    str_compute = ""
                    for val in codes:
                        if val:
                            if val == code:
                                str_compute += val + '=1'
                            else:
                                str_compute += val + '=0'
                            str_compute += '\r\n'
                    code_exec = compile(str_compute, '', 'exec')
                    exec(code_exec)
                    sum_value = eval(formula)

                    if code not in ['sum', 'sum_if_pos', 'sum_if_neg']:
                        child = dict_journal_item.setdefault(code, {'pos': 1, 'child': [], 'code': code})
                        child['pos'] = sum_value
                        dict_journal_item[line.code]['child'].append(child)

        code_group_expenses = []
        code_group_income = []

        # Get the tree of net profit and loss in dict_journal_item
        ni_tree = dict_journal_item[ni.code]
        stack_child = ni_tree['child']
        while len(stack_child):
            node = stack_child.pop()
            childs = node['child']
            if childs:
                for child in childs:
                    child['pos'] *= node['pos']
                stack_child += childs
            else:
                if node['pos'] > 0:
                    code_group_income.append(node['code'])
                else:
                    code_group_expenses.append(node['code'])

        domain_group_expenses = self.env['account.financial.html.report.line'] \
            .search([('code', 'in', code_group_expenses)]) \
            .mapped(lambda g: ast.literal_eval(g.domain))
        domain_group_income = self.env['account.financial.html.report.line'] \
            .search([('code', 'in', code_group_income)]) \
            .mapped(lambda g: ast.literal_eval(g.domain))

        expenses_domain = expression.OR(domain_group_expenses)
        income_domain = expression.OR(domain_group_income)
        tables, query_expenses_clause, where_params = self.env["account.move.line"]._query_get(domain=expenses_domain)

        sql_params = [period_type, date_from, date_to]
        sql_params.extend(where_params)

        income_group_data = self.env['account.move.line'].summarize_group_account(date_from, date_to,
                                                                                  period_type, income_domain)
        expense_group_data = self.env['account.move.line'].summarize_group_account(date_from, date_to,
                                                                                   period_type, expenses_domain)
        total_income, income_values = self.get_values_for_graph(date_from, date_to,
                                                                period_type, income_group_data,
                                                                'date_in_period', ['total_balance'],
                                                                pos=-1)
        total_expense, expense_values = self.get_values_for_graph(date_from, date_to,
                                                                  period_type, expense_group_data,
                                                                  'date_in_period', ['total_balance'])
        graph_data = [
            {
                'key': _('Income'),
                'values': income_values[0],
                'color': COLOR_INCOME
            }, {
                'key': _('Expenses'),
                'values': expense_values[0],
                'color': COLOR_EXPENSE
            }]
        info_data = [
            {
                'name': _('Net Income'),
                'summarize': format_currency(self, total_income[0] - total_expense[0])
            }, {
                'name': _('Income'),
                'summarize': format_currency(self, total_income[0])
            }, {
                'name': _('Expenses'),
                'summarize': format_currency(self, total_expense[0])
            }]

        return {'graph_data': graph_data, 'info_data': info_data}

    @api.model
    def retrieve_sales(self, date_from, date_to, period_type):
        """ API is used to response untaxed amount of all invoices in system that get
        from account_invoice.

        :param date_from: the start date to summarize data, have type is datetime
        :param date_to: the end date to summarize data, that have type is datetime
        :param period_type: is type of period to summarize data, we have 4 selections are
                ['week', 'month', 'quarter', 'year']
        :return: Json
                {
                    'graph_data': [{json to render graph data}]
                    'info_data': [{'name': 'the label will show for summarize data', 'summarize': 'summarize data'}]
                }
        """

        graph_data = []
        info_data = []
        summarize = 0.0
        extra_graph_setting = {}

        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        periods = get_list_period_by_type(self, date_from, date_to, period_type)

        currency = """  SELECT c.id,
                               COALESCE((SELECT r.rate FROM res_currency_rate r
                                         WHERE r.currency_id = c.id AND r.name <= %s
                                           AND (r.company_id IS NULL OR r.company_id IN %s)
                                         ORDER BY r.company_id, r.name DESC
                                         LIMIT 1), 1.0) AS rate
                        FROM res_currency c"""

        transferred_currency = """select ai.date_invoice, c.rate * ai.amount_untaxed as amount_tran, state, company_id
                                  from account_invoice as ai
                                         left join ({currency_table}) as c
                                           on ai.currency_id = c.id""".format(currency_table=currency, )

        query = """ SELECT date_part('year', aic.date_invoice::date) as year,
                           date_part(%s, aic.date_invoice::date) AS period,
                           MIN(aic.date_invoice) as date_in_period,
                           SUM(aic.amount_tran) as amount_untaxed
                    FROM ({transferred_currency_table}) as aic
                    WHERE date_invoice >= %s AND
                          date_invoice <= %s AND
                          aic.state NOT IN ('draft',  'cancel') AND
                          aic.company_id IN %s
                    GROUP BY year, period
                    ORDER BY year, period;""".format(transferred_currency_table=transferred_currency, )

        company_ids = get_list_companies_child(self.env.user.company_id)
        name = fields.Date.today()
        self.env.cr.execute(query, (period_type, name, tuple(company_ids), date_from, date_to, tuple(company_ids),))
        data_fetch = self.env.cr.dictfetchall()
        index_period = 0
        past_sale_values = []
        future_sale_values = []

        for data in data_fetch:
            while not (periods[index_period][0] <= data['date_in_period'] <= periods[index_period][1]) \
                    and index_period < len(periods):
                push_to_list_values_to_sales(
                    past_sale_values, future_sale_values,
                    0, index_period + 1,
                    periods[index_period], period_type)
                index_period += 1
            if index_period < len(periods):
                amount_untaxed = data.get('amount_untaxed', False)
                if not isinstance(amount_untaxed, bool):
                    push_to_list_values_to_sales(
                        past_sale_values, future_sale_values,
                        amount_untaxed, index_period + 1,
                        periods[index_period], period_type)
                    summarize += amount_untaxed
                index_period += 1

        # Append value miss in the future with the value 0 for each period
        while index_period < len(periods):
            push_to_list_values_to_sales(
                past_sale_values, future_sale_values,
                0, index_period + 1,
                periods[index_period], period_type)
            index_period += 1

        graph_data.append({
            'values': past_sale_values,
            'key': _('Sales'),
            'color': COLOR_SALE_PAST
        })
        if len(future_sale_values):
            graph_data.append({
                'values': future_sale_values,
                'key': _('Future'),
                'color': COLOR_SALE_FUTURE
            })
        info_data.append({'name': _('Total Amount'), 'summarize': format_currency(self, summarize)})
        return {'graph_data': graph_data, 'info_data': info_data, 'extra_graph_setting': extra_graph_setting}

    @api.model
    def retrieve_cash(self, date_from, date_to, period_type):
        """ API is used to response total amount of cash in/out base on
        account move in system. That is the account move of account have
        name is 'Bank and Cash' in the system beside that, also return
        any info relate to show in "Cash" kanban section.

        :param date_from: the start date to summarize data, have type is datetime
        :param date_to: the end date to summarize data, that have type is datetime
        :param period_type: is type of period to summarize data, we have 4 selections are
                ['week', 'month', 'quarter', 'year']
        :return: Json
                {
                    'graph_data': [{json to render graph data}]
                    'info_data': [{'name': 'the label will show for summarize data', 'summarize': 'summarize data'}]
                }
        """

        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        periods = get_list_period_by_type(self, date_from, date_to, period_type)
        type_account_id = self.env.ref('account.data_account_type_liquidity').id
        query = """SELECT date_part('year', aml.date::date) as year,
                              date_part(%s, aml.date::date) AS period,
                              MIN(aml.date) as date_in_period,
                              SUM(aml.debit) as total_debit,
                              SUM(aml.credit) as total_credit
                        FROM account_move_line as aml
                        INNER JOIN account_move as am
                        ON aml.move_id = am.id
                        INNER JOIN account_account as aa
                        ON aml.account_id = aa.id
                        INNER JOIN account_account_type as aat
                        ON aa.user_type_id = aat.id
                        WHERE aml.date >= %s AND 
                              aml.date <= %s AND
                              am.state = 'posted' AND
                              aat.id = %s AND 
                              aml.company_id IN %s
                        GROUP BY year, period
                        ORDER BY year, period;"""

        company_ids = get_list_companies_child(self.env.user.company_id)
        self.env.cr.execute(query, (period_type, date_from, date_to, type_account_id, tuple(company_ids),))
        data_fetch = self.env.cr.dictfetchall()
        index_period = 0
        cash_in = []
        cash_out = []
        net_cash = []
        cash_data = [cash_in, cash_out, net_cash]
        for data in data_fetch:
            while not (periods[index_period][0] <= data['date_in_period'] <= periods[index_period][1]) and \
                    index_period < len(periods):
                push_to_list_lists_at_timestamp(cash_data, [0, 0, 0], periods[index_period], period_type)
                index_period += 1
            if index_period < len(periods):
                push_to_list_lists_at_timestamp(cash_data,
                                                [
                                                    data['total_debit'],
                                                    - data['total_credit'],
                                                    data['total_debit'] - data['total_credit']
                                                ],
                                                periods[index_period], period_type)
                index_period += 1

        while index_period < len(periods):
            push_to_list_lists_at_timestamp(cash_data, [0, 0, 0], periods[index_period], period_type)
            index_period += 1

        # Create chart data
        graph_data = [{
            'key': _('Cash in'),
            'values': cash_in,
            'color': COLOR_CASH_IN,
            'type': 'bar',
            'yAxis': 1
        }, {
            'key': _('Cash out'),
            'values': cash_out,
            'color': COLOR_CASH_OUT,
            'type': 'bar',
            'yAxis': 1
        }, {
            'key': _('Net cash'),
            'values': net_cash,
            'color': COLOR_NET_CASH,
            'type': 'line',
            'yAxis': 1
        }]

        # Create info to show in head of chart
        sum_cash_in = sum(item['y'] for item in cash_in)
        sum_cash_out = sum(item['y'] for item in cash_out)
        info_data = [{
            'name': _('Cash in'),
            'summarize': format_currency(self, sum_cash_in)
        }, {
            'name': _('Cash out'),
            'summarize': format_currency(self, sum_cash_out)
        }, {
            'name': _('Net cash'),
            'summarize': format_currency(self, sum_cash_in + sum_cash_out)
        }]
        return {'graph_data': graph_data, 'info_data': info_data}

    ########################################################
    # GENERAL FUNCTION SUPPORT API
    ########################################################
    def get_values_for_graph(self, date_from, date_to, period_type,
                             data_group, field_date_in_period='date_in_period',
                             list_fields_data=[], pos=1):
        """ function return the values to render the graph base on the range of time, period type,
        data is list of dictionary contain data have summarize from database

        :param date_from:
        :param date_to:
        :param period_type:
        :param data_group:
        :param field_date_in_period:
        :param list_fields_data:
        :return:
        """
        index_period = 0
        len_of_list = len(list_fields_data)
        list_data_return = []
        if len_of_list:
            periods = get_list_period_by_type(self, date_from, date_to, period_type)
            list_zero_value = [0 for i in range(len_of_list)]
            list_data_return = [[] for i in range(len_of_list)]
            summarize = list_zero_value.copy()

            for data in data_group:
                list_data_value = [data[key] * pos for key in list_fields_data]
                while not (periods[index_period][0] <= data[field_date_in_period] <= periods[index_period][1]) and \
                        index_period < len(periods):
                    push_to_list_lists_at_timestamp(list_data_return,
                                                    list_zero_value,
                                                    [periods[index_period][0]], period_type)
                    index_period += 1
                if index_period < len(periods):
                    push_to_list_lists_at_timestamp(list_data_return,
                                                    list_data_value,
                                                    [periods[index_period][0]], period_type)
                    summarize = [sum(x) for x in zip(summarize, list_data_value)]
                    index_period += 1

            while index_period < len(periods):
                push_to_list_lists_at_timestamp(list_data_return,
                                                list_zero_value,
                                                [periods[index_period][0]], period_type)
                index_period += 1

        return summarize, list_data_return
