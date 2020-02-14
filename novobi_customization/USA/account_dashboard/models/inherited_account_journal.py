# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.


import json

from ..utils.graph_utils import get_json_data_for_selection, push_to_list_lists_at_timestamp, get_json_render
from ..models.usa_journal import CUSTOMER_INVOICE, VENDOR_BILLS, COLOR_PAID_INVOICE, COLOR_OPEN_INVOICES, \
    COLOR_OPEN_BILLS, COLOR_PAID_BILLS
from ..utils.utils import get_list_companies_child
from ..utils.time_utils import BY_DAY, BY_WEEK, BY_MONTH, BY_QUARTER, BY_FISCAL_YEAR, \
    get_start_end_date_value_with_delta, BY_YEAR, \
    get_same_date_delta_period, get_list_period_by_type
from ..models.usa_journal import COLOR_VALIDATION_DATA
from odoo import models, api, _, fields
from odoo.tools.misc import formatLang
from datetime import datetime, date


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.one
    def _kanban_dashboard_graph(self):
        res = super(AccountJournal, self)._kanban_dashboard_graph()
        if self.type in ['sale', 'purchase']:
            type_data = "bar"
            extend_mode, graph_data = self.get_general_kanban_section_data()
            selection = []
            get_json_data_for_selection(self, selection, self.period_by_month, self.default_period_by_month)
            function_retrieve = 'retrieve_account_invoice'
            extra_param = [self.type]

            self.kanban_dashboard_graph = json.dumps(
                get_json_render(type_data, False,
                                graph_data, self.type,
                                selection, function_retrieve, extra_param, self.currency_id.id))
        elif self.type in ['cash', 'bank']:
            type_data = "line"
            graph_data = self.get_line_graph_datas()
            self.format_graph_data_of_bank(graph_data)
            for line in graph_data:
                for idx, value in enumerate(line['values']):
                    value['name'] = value['x']
                    value['x'] = idx
            selection = []
            function_retrieve = ''
            extra_param = []
            # data_type, extend, data_render, name_card, selection, function_retrieve)
            self.kanban_dashboard_graph = json.dumps(get_json_render(type_data, False,
                                                                     graph_data, self.type,
                                                                     selection, function_retrieve, extra_param, self.currency_id.id))
        return res

    @api.one
    def _kanban_right_info_graph(self):
        if self.type in ['bank']:

            graph_data = [{
                'values': [{
                    'value': self.get_balance_per_book(),
                    'label': 'Balance per Book',
                    'color': '#f90'
                }, {
                    'value': self.get_balance_per_bank(),
                    'label': 'Balance per Bank',
                    'color': '#009e0f'
                }],
                'title': '',
                'key': '',
                'color': COLOR_VALIDATION_DATA}]
            selection = []
            function_retrieve = ''
            extra_param = []
            extra_graph_setting = {
                'stacked': False,
                'showXAxis': True,
                'showYAxis': False,
                'showValues': True,
                'hideGird': True,
                'marginLeft': 100,
                'height': 60
            }
            self.kanban_right_info_graph = json.dumps(get_json_render('horizontal_bar', False,
                                                                      graph_data, self.type,
                                                                      selection, function_retrieve, extra_param, self.currency_id.id,
                                                                      extra_graph_setting))
        else:
            self.kanban_right_info_graph = ''

    period_by_month = [{'n': 'This Month', 'd': 0, 't': BY_MONTH},
                       {'n': 'This Quarter', 'd': 0, 't': BY_QUARTER},
                       {'n': 'This Fiscal Year', 'd': 0, 't': BY_FISCAL_YEAR},
                       {'n': 'Last Month', 'd': -1, 't': BY_MONTH},
                       {'n': 'Last Quarter', 'd': -1, 't': BY_QUARTER},
                       {'n': 'Last Fiscal Year', 'd': -1, 't': BY_FISCAL_YEAR}, ]

    default_period_by_month = 'This Fiscal Year'
    kanban_right_info_graph = fields.Text(compute='_kanban_right_info_graph')

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

    @api.model
    def retrieve_account_invoice(self, date_from, date_to, period_type=BY_MONTH, type_invoice=VENDOR_BILLS):
        """ API is used to response total amount of open/paid account invoice
        and any info relate to show in "Customer Invoices" and "Vendor Bills"
        kanban sections.

        :param date_from: the start date to summarize data, have type is datetime
        :param date_to: the end date to summarize data, that have type is datetime
        :param period_type: is type of period to summarize data, we have 4 selections are
                ['week', 'month', 'quarter', 'year']
        :param type_invoice: two case is out_invoice for "Customer Invoices" and in_invoice in "Vendor Bills"
        :return: Json
                {
                    'graph_data': [{json to render graph data}]
                    'info_data': [{'name': 'the label will show for summarize data', 'summarize': 'summarize data'}]
                }
        """
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        periods = get_list_period_by_type(self, date_from, date_to, period_type)

        type_invoice_select = 'in_invoice' if type_invoice == VENDOR_BILLS else 'out_invoice'

        currency = """  SELECT c.id,
                               COALESCE((SELECT r.rate FROM res_currency_rate r
                                         WHERE r.currency_id = c.id AND r.name <= %s
                                           AND (r.company_id IS NULL OR r.company_id IN %s)
                                         ORDER BY r.company_id, r.name DESC
                                         LIMIT 1), 1.0) AS rate
                        FROM res_currency c"""

        transferred_currency = """SELECT ai.date_invoice, c.rate * ai.residual_signed AS residual_signed_tran, 
                                        c.rate * ai.amount_total_signed AS amount_total_signed_tran, state, type, company_id
                                  FROM account_invoice AS ai
                                         LEFT JOIN ({currency_table}) AS c
                                           ON ai.currency_id = c.id""".format(currency_table=currency, )

        query = """SELECT date_part('year', aic.date_invoice::date) as year,
                                  date_part(%s, aic.date_invoice::date) AS period,
                                  COUNT(*),
                                  MIN(aic.date_invoice) as date_in_period,
                                  SUM(aic.amount_total_signed_tran) as total,
                                  SUM(aic.residual_signed_tran) as amount_due
                            FROM ({transferred_currency}) as aic
                            WHERE aic.date_invoice >= %s AND 
                                  aic.date_invoice <= %s AND
                                  aic.state in ('open', 'in_payment', 'paid') AND
                                  aic.type = %s AND 
                                  aic.company_id IN %s
                            GROUP BY year, period
                            ORDER BY year, period;""".format(transferred_currency=transferred_currency, )

        company_ids = get_list_companies_child(self.env.user.company_id)
        name = fields.Date.today()
        self.env.cr.execute(query, (period_type, name, tuple(company_ids), date_from, date_to, type_invoice_select, tuple(company_ids),))
        data_fetch = self.env.cr.dictfetchall()
        index_period = 0
        opens = []
        paids = []
        account_invoices = [opens, paids]
        for data in data_fetch:
            while not (periods[index_period][0] <= data['date_in_period'] <= periods[index_period][1]) \
                    and index_period < len(periods):
                push_to_list_lists_at_timestamp(account_invoices,
                                                [0, 0],
                                                [periods[index_period][0]], period_type)
                index_period += 1
            if index_period < len(periods):
                push_to_list_lists_at_timestamp(account_invoices,
                                                [data['amount_due'], data['total'] - data['amount_due']],
                                                [periods[index_period][0]], period_type)
                index_period += 1

        while index_period < len(periods):
            push_to_list_lists_at_timestamp(account_invoices,
                                            [0, 0],
                                            [periods[index_period][0]], period_type)
            index_period += 1

        # Create chart data
        graph_data = [{
            'key': _('Open ' + ('Invoices' if type_invoice == CUSTOMER_INVOICE else 'Bills')),
            'values': opens,
            'color': COLOR_OPEN_INVOICES if type_invoice == CUSTOMER_INVOICE else COLOR_OPEN_BILLS,
        }, {
            'key': _('Paid ' + ('Invoices' if type_invoice == CUSTOMER_INVOICE else 'Bills')),
            'values': paids,
            'color': COLOR_PAID_INVOICE if type_invoice == CUSTOMER_INVOICE else COLOR_PAID_BILLS,
        }]
        info_data = []
        return {
            'graph_data': graph_data,
            'info_data': info_data,
            'extra_graph_setting': {'stacked': True}}

    def get_balance_per_book(self):
        account_sum = 0
        if self.type in ['bank', 'cash']:
            # Get the number of items to reconcile for that bank journal
            self.env.cr.execute("""SELECT COUNT(DISTINCT(line.id))
                                                        FROM account_bank_statement_line AS line
                                                        LEFT JOIN account_bank_statement AS st
                                                        ON line.statement_id = st.id
                                                        WHERE st.journal_id IN %s AND st.state = 'open' AND line.amount != 0.0 AND line.account_id IS NULL
                                                        AND not exists (select 1 from account_move_line aml where aml.statement_line_id = line.id)
                                                    """, (tuple(self.ids),))

            # optimization to read sum of balance from account_move_line
            account_ids = tuple(
                ac for ac in [self.default_debit_account_id.id, self.default_credit_account_id.id] if ac)
            if account_ids:
                amount_field = 'aml.balance' if (
                        not self.currency_id or self.currency_id == self.company_id.currency_id) else 'aml.amount_currency'
                query = """SELECT sum(%s) FROM account_move_line aml
                                                       LEFT JOIN account_move move ON aml.move_id = move.id
                                                       WHERE aml.account_id in %%s
                                                       AND move.date <= %%s AND move.state = 'posted';""" % (
                    amount_field,)
                self.env.cr.execute(query, (account_ids, fields.Date.today(),))
                query_results = self.env.cr.dictfetchall()
                if query_results and query_results[0].get('sum') != None:
                    account_sum = query_results[0].get('sum')
        return account_sum

    def get_balance_per_bank(self):
        last_balance = 0
        if self.type in ['bank', 'cash']:
            last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)],
                                                                       order="date desc, id desc", limit=1)
            last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0
        return last_balance

    ########################################################
    # GENERAL FUNCTIONS
    ########################################################
    def _get_tuple_type(self):
        tuple_type = None
        if self.type == 'sale':
            tuple_type = tuple(['out_invoice'])
        elif self.type == 'purchase':
            tuple_type = tuple(['in_invoice'])
        return tuple_type

    def format_graph_data_of_bank(self, graph_data):
        for item in graph_data:
            item['key'] = item.get('key', '').replace(':', '')
            last_item = item.get('values')[-1]
            if last_item:
                last_item['x'] = 'Now'

            # change the color of line and also area of graph
            item['color'] = '#fd7e14'

    def _get_bills_aging_range_time_query(self, tuple_type, lower_bound_range=None, upper_bound_range=None):
        """
        Returns a tuple containing as its first element the SQL query used to
        gather the bills in open state data, aging date in range and the arguments
        dictionary to use to run it as its second.
        """
        lower_bound_condition = 'AND aging_days >= %s' % lower_bound_range \
            if isinstance(lower_bound_range, int) \
            else ''
        upper_bound_condition = 'AND aging_days <= %s' % upper_bound_range \
            if isinstance(upper_bound_range, int) \
            else ''
        query = """SELECT state, amount_total, residual_signed, currency_id AS currency, 
                            type, date_invoice, company_id
                  FROM account_invoice
                  WHERE journal_id = %(journal_id)s
                    AND type in %(tuple_type)s
                    AND state = 'open' 
                    {lower_bound_condition}
                    {upper_bound_condition};""".format(
            lower_bound_condition=lower_bound_condition,
            upper_bound_condition=upper_bound_condition)
        return (query,
                {
                    'journal_id': self.id,
                    'tuple_type': tuple_type,
                })

    def _get_draft_bills_query(self):
        """
        Returns a tuple containing as its first element the SQL query used to
        gather the bills in draft state data, and the arguments
        dictionary to use to run it as its second.
                """
        (old_query, query_args) = super(AccountJournal, self)._get_draft_bills_query()

        # remove semi-colon
        query_converted = old_query[:max(len(old_query) - 1, 0)]

        query = """SELECT *
                  FROM ({old_query}) as temp
                  WHERE type in %(type)s;""".format(old_query=query_converted)
        query_args.update({'type': self._get_tuple_type()})
        return (query, query_args)

    def _count_results_and_sum_residual_signed(self, results_dict, target_currency):
        """ Loops on a query result to count the total number of invoices and sum
        their amount_total field (expressed in the given target currency).
        """
        rslt_count = 0
        rslt_sum = 0.0
        for result in results_dict:
            cur = self.env['res.currency'].browse(result.get('currency'))
            company = self.env['res.company'].browse(result.get('company_id')) or \
                      self.env.user.company_id
            rslt_count += 1
            type_factor = result.get('type') in ('in_refund', 'out_refund') and -1 or 1
            rslt_sum += type_factor * cur._convert(
                result.get('residual_signed'), target_currency, company,
                result.get('date_invoice') or fields.Date.today())
        return (rslt_count, rslt_sum)

    @api.multi
    def get_journal_dashboard_datas(self):
        datas = super(AccountJournal, self).get_journal_dashboard_datas()
        currency = self.currency_id or self.company_id.currency_id
        if self.type == 'bank':
            datas.update({
                'is_credit_card': self.is_credit_card,
            })
            if self.is_credit_card:
                datas.update({
                    'unpaid_balance_statement': formatLang(self.env, currency.round(self.partner_id.debit) + 0.0,
                                                           currency_obj=currency),
                })
        elif self.type in ['sale', 'purchase']:
            tuple_type = self._get_tuple_type()

            (query, query_args) = self._get_bills_aging_range_time_query(tuple_type, lower_bound_range=0)
            self.env.cr.execute(query, query_args)
            query_results_open_invoices = self.env.cr.dictfetchall()

            (query, query_args) = self._get_bills_aging_range_time_query(tuple_type, lower_bound_range=1,
                                                                         upper_bound_range=30)
            self.env.cr.execute(query, query_args)
            query_results_in_month = self.env.cr.dictfetchall()

            (query, query_args) = self._get_bills_aging_range_time_query(tuple_type, lower_bound_range=31)
            self.env.cr.execute(query, query_args)
            query_results_over_month = self.env.cr.dictfetchall()

            (number_open_invoices, sum_open_invoices) = self._count_results_and_sum_residual_signed(query_results_open_invoices, currency)
            (number_in_month, sum_in_month) = self._count_results_and_sum_residual_signed(query_results_in_month,
                                                                                          currency)
            (number_over_month, sum_over_month) = self._count_results_and_sum_residual_signed(query_results_over_month,
                                                                                              currency)

            datas.update({
                'number_open_invoices': number_open_invoices,
                'sum_open_invoices': formatLang(self.env, currency.round(sum_open_invoices) + 0.0, currency_obj=currency),
                'number_in_month': number_in_month,
                'sum_in_month': formatLang(self.env, currency.round(sum_in_month) + 0.0, currency_obj=currency),
                'number_over_month': number_over_month,
                'sum_over_month': formatLang(self.env, currency.round(sum_over_month) + 0.0, currency_obj=currency),
                # 'number_draft': number_draft,
                # 'sum_draft': formatLang(self.env, currency.round(sum_draft) + 0.0, currency_obj=currency),
            })
        return datas

    @api.multi
    def open_action(self):
        domain = self._context.get('use_domain', [])
        action = super(AccountJournal, self).open_action()
        # remove any domain related to field type
        action['domain'] = [cond for cond in action['domain'] if cond[0] != 'type']

        # append new domain related to any customs domain of dev passed from file xml
        action['domain'] += domain

        # append new domain related to filed type
        if self.type == 'sale':
            action['domain'].append(('type', 'in', ['out_invoice']))

        elif self.type == 'purchase':
            action['domain'].append(('type', 'in', ['in_invoice']))

        action['domain'].append(('journal_id', '=', self.id))

        return action

    ########################################################
    # INITIAL DATA
    ########################################################
    @api.model
    def change_status_favorite(self):
        cashes = self.search([('type', '=', 'cash')])
        for cash in cashes:
            cash.write({'show_on_dashboard': False})
