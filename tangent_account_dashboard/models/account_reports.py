# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import date, timedelta

class TangentAccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def _apply_date_filter(self, options):
        if options.get('date') and options['date'].get('filter'):
            options_filter = options['date']['filter']
            if options_filter == 'last_week':
                today = date.today()
                date_index = (today.weekday() + 1) % 7
                sun = today - timedelta(7 + date_index)
                sat = today - timedelta(7 + date_index - 6)
                options['date']['date_from'] = fields.Date.to_string(sun)
                options['date']['date_to'] = fields.Date.to_string(sat)
                options['date']['filter'] = 'custom'

        super(TangentAccountReport, self)._apply_date_filter(options)
