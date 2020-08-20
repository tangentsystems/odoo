# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import date, timedelta

class TangentAccountReport(models.AbstractModel):
    _inherit = 'account.report'

    @api.model
    def _init_filter_date(self, options, previous_options=None):
        if previous_options and previous_options.get('date') and previous_options['date'].get('filter'):
            options_filter = previous_options['date']['filter']
            if options_filter == 'last_week':
                sun, sat = self._get_last_week_days()
                previous_options['date']['date_from'] = fields.Date.to_string(sun)
                previous_options['date']['date_to'] = fields.Date.to_string(sat)
                previous_options['date']['filter'] = 'custom'
            if options_filter == 'end_of_last_week':
                _, sat = self._get_last_week_days()
                previous_options['date']['date_from'] = fields.Date.to_string(date(sat.year, sat.month, 1))
                previous_options['date']['date_to'] = fields.Date.to_string(sat)
                previous_options['date']['filter'] = 'custom'

        super(TangentAccountReport, self)._init_filter_date(options, previous_options)

    def _get_last_week_days(self):
        today = date.today()
        date_index = (today.weekday() + 1) % 7
        sun = today - timedelta(7 + date_index)
        sat = today - timedelta(7 + date_index - 6)

        return sun, sat
