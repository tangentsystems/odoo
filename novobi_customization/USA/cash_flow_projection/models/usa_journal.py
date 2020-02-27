# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2019 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import api, fields, models, _
from datetime import datetime
from odoo.addons.account_dashboard.models.usa_journal import COLOR_PROJECTED_CASH_IN, COLOR_PROJECTED_CASH_OUT, COLOR_PROJECTED_BALANCE, CASH_FORECAST
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.account_dashboard.utils.utils import format_currency


class Account(models.Model):
    _inherit = 'usa.journal'
    
    @api.multi
    def action_open_cashflow_forecast_summary(self):
        self.env.user.company_id.cash_flow_last_period_type = 'month'
        action = self.env.ref('cash_flow_projection.cash_flow_projection_action_client').read()[0]
        return action
    
    @api.model
    def retrieve_cash_forecast(self, date_from, date_to, period_type):
        index_period = 0
        open_balance_date = datetime.today()
        cash_in = []
        cash_out = []
        net_cash = []
        # Get record options
        record_options = self.env['cash.flow.transaction.type'].get_all_record()
        record_options.update({
            'period': 'month',
            'num_period': 7,
            'from_chart': True,
        })
        # Retrieve data from cash flow projection
        result_dict, num_period, period_unit = self.env['cash.flow.projection'].get_data(record_options)
        data_dict = result_dict.get('periods') or []
        opening_balance = len(data_dict) > 0 and data_dict[0].get('opening_balance') or 0.0
        for period in data_dict:
            cash_in.append({
                'name': period.get('period'),
                'x': index_period,
                'y': period.get('total_cash_in'),
            })
            cash_out.append({
                'name': period.get('period'),
                'x': index_period,
                'y': -period.get('total_cash_out'),
            })
            net_cash.append({
                'name': period.get('period'),
                'x': index_period,
                'y': period.get('closing_balance'),
            })
            index_period += 1

        # Create chart data
        graph_data = [{
            'key': _('Projected Cash in'),
            'values': cash_in,
            'color': COLOR_PROJECTED_CASH_IN,
            'type': 'bar',
            'yAxis': 1
        }, {
            'key': _('Projected Cash out'),
            'values': cash_out,
            'color': COLOR_PROJECTED_CASH_OUT,
            'type': 'bar',
            'yAxis': 1
        }, {
            'key': _('Balance Carried Forward'),
            'values': net_cash,
            'color': COLOR_PROJECTED_BALANCE,
            'type': 'line',
            'yAxis': 1
        }]

        # Create info to show in head of chart
        sum_cash_in = sum(item['y'] for item in cash_in)
        sum_cash_out = sum(item['y'] for item in cash_out)
        info_data = [{
            'name': _('Total Projected Cash in'),
            'title': _('This is total projected cash-in in the next 6 months'),
            'summarize': format_currency(self, sum_cash_in)
        }, {
            'name': _('Total Projected Cash out'),
            'title': _('This is total projected cash-out in the next 6 months'),
            'summarize': format_currency(self, sum_cash_out)
        }, {
            'name': _('Balance of Bank & Cash as of {}'.format(open_balance_date.strftime(DEFAULT_SERVER_DATE_FORMAT))),
            'summarize': format_currency(self, opening_balance)
        }]
        return {'graph_data': graph_data, 'info_data': info_data}

    @api.multi
    def open_action_label(self):
        """ Function return action based on type for related journals

        :return:
        """
        
        if self.type == CASH_FORECAST:
            return self.action_open_cashflow_forecast_summary()
        else:
            return super().open_action_label()
        