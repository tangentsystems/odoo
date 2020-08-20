# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar
import json


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _kanban_dashboard_graph(self):
        super(AccountJournal, self)._kanban_dashboard_graph()

        for record in self:
            today = date.today()
            end_of_current_month_day = calendar.monthrange(today.year, today.month)[1]
            end_of_current_month = date(today.year, today.month, end_of_current_month_day)
            last_11_months = end_of_current_month - relativedelta(months=11)
            start_of_last_12_months = date(last_11_months.year, last_11_months.month, 1)

            if record.type in ['sale', 'purchase']:
                dashboard_data = json.loads(record.kanban_dashboard_graph)
                dashboard_data[0]['selection'].append({
                    'n': 'Last 12 Months',
                    's': fields.Date.to_string(start_of_last_12_months),
                    'e': fields.Date.to_string(end_of_current_month),
                    'd': False,
                    'k': 'month'
                })
                record.kanban_dashboard_graph = json.dumps(dashboard_data)
