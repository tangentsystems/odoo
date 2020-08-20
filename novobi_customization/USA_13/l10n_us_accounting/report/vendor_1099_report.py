from odoo import models, api, _
from odoo.addons.web.controllers.main import clean_action


class report_vendor_1099(models.AbstractModel):
    _name = "vendor.1099.report"
    _description = "Vendor 1099 Report"
    _inherit = 'account.report'

    filter_date = {'date_from': '', 'date_to': '', 'filter': 'this_year'}

    def _get_columns_name(self, options):
        return [{'name': 'Name'},
                {'name': 'EIN/SSN Number'},
                {'name': 'Address'},
                {'name': 'Amount Paid', 'class': 'number'}]

    def _get_templates(self):
        templates = super(report_vendor_1099, self)._get_templates()
        return templates

    def _get_report_name(self):
        return _('Vendor 1099 Report')

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        partners = self._get_result_lines(options)

        for p in partners:
            vals = {
                'id': p['partner_odoo_id'],
                'name': p['partner_name'],
                'level': 2,
                'class': 'o_account_reports_level3 no-margin',
                'caret_options': 'vendor.1099',
                'columns': [{'name': v} for v in [p['partner_ssn'], p['partner_address'], self.format_value(p['total_balance'])]],
            }
            lines.append(vals)

        return lines

    def _get_result_lines(self, options):
        cr = self.env.cr

        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        company_ids = self.env.context.get('company_ids', (self.env.user.company_id.id,))

        sql_params = [date_from, date_to, tuple(company_ids)]

        query = """
        SELECT l.partner_id AS partner_odoo_id,
            partner.name AS partner_name,
            partner.vat AS partner_ssn,
            CONCAT(partner.street, ' ', partner.street2, ' ', partner.city, ' ', res_country_state.code, ' ', partner.zip) AS partner_address,
            SUM(l.debit) - SUM(l.credit) AS total_balance
        
        FROM account_move_line AS l
            JOIN res_partner AS partner ON l.partner_id = partner.id
            JOIN account_account ON l.account_id = account_account.id
            JOIN account_move AS am ON l.move_id = am.id
            JOIN account_journal ON l.journal_id = account_journal.id
            LEFT JOIN res_country_state ON partner.state_id = res_country_state.id
            
        WHERE
            am.state = 'posted' AND
            account_account.internal_type = 'payable' AND
            account_journal.type in ('cash', 'bank') AND
            (l.date BETWEEN %s AND %s) AND
            partner.vendor_eligible_1099 = True AND
            l.company_id IN %s
            
        GROUP BY partner_odoo_id, partner_ssn, partner_address, partner_name
        HAVING SUM(l.debit) - SUM(l.credit) != 0
        ORDER BY UPPER(partner.name);
        """

        cr.execute(query, sql_params)
        partners = cr.dictfetchall()
        return partners

    def open_vendor_1099(self, options, params):
        action = self.env.ref('account.action_account_moves_all_a').read()[0]
        action = clean_action(action)

        if params and 'id' in params and options:
            partner_id = params['id']
            date_from = options['date']['date_from']
            date_to = options['date']['date_to']

            action['domain'] = [('partner_id', '=', partner_id), ('move_id.state', '=', 'posted'),
                                ('account_id.internal_type', '=', 'payable'),
                                ('journal_id.type', 'in', ['cash', 'bank']),
                                ('date', '>=', date_from), ('date', '<=', date_to)]

        return action
