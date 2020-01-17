# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.


import xlsxwriter
import io
import ast
from odoo import models, api, _, fields
from xlsxwriter import utility
from ..utils.budget_utils import get_list_period_by_type, _divide_line, format_number, _get_balance_sheet_value


class BudgetReport(models.AbstractModel):
    _inherit = 'account.report'
    _name = 'usa.budget.report'
    _description = 'Budget Report'

    filter_groupby = {'filter': 'Monthly'}

    def _get_templates(self):
        templates = super(BudgetReport, self)._get_templates()
        templates['line_template'] = 'account_budget_advanced.line_template_budget_report_screen'
        templates['main_template'] = 'account_budget_advanced.template_budget_entry_screen'
        templates['search_template'] = 'account_budget_advanced.search_template_budget_report_screen'
        templates['main_table_header_template'] = 'account_budget_advanced.main_table_header_budget_report'
        return templates

    def _get_report_name(self):
        budget = self._get_crossovered_budget_obj()
        return budget.name

    def get_report_filename(self, options):
        if options and options.get('crossovered_budget_id', False):
            budget = self.env['crossovered.budget'].browse(options['crossovered_budget_id'])
            return budget.name.lower().replace(' ', '_')

    def _get_columns_name(self, options, export=None, budget=None):
        columns = [{'name': 'Account', 'rowspan': 2}]

        daterange_list = options.get('daterange_list', False)
        filter_groupby = options['groupby']['filter']

        budget = budget or options['crossovered_budget']

        if export:
            daterange_list = self._get_daterange_list(options, budget)

        if budget.budget_type == 'profit':
            columns.extend([{
                'name': item[0].strftime("%b %Y") if filter_groupby == 'Monthly' else
                item[0].strftime("%b %Y") + ' - ' + item[1].strftime("%b %Y"),
                'class': 'number value_column ',
                'colspan': 4
            } for item in daterange_list])

            columns.append({'name': 'Total',
                            'class': 'number total_column',
                            'colspan': 4})
        else:
            columns.extend([{
                'name': "As of " + item[1].strftime('%m/%d/%Y'),
                'class': 'number value_column ',
                'colspan': 4
            } for item in daterange_list])

        return columns

    def _get_reports_buttons(self):
        return []

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = options.get('lines', [])

        return lines

    @api.multi
    def _get_dict_lines(self, children_lines, column_number, crossovered_budget, daterange_list,
                        financial_report, currency_table, is_profit_budget):
        final_result_table = []
        AccountAccount = self.env['account.account']
        empty = [0.0 for i in range(column_number)]
        analytic_account_id = crossovered_budget.analytic_account_id

        # build comparison table
        for line in children_lines:
            domain_ids = {}
            lines = []
            balance_sheet_dict = {}
            class_name = ' expense_budget' if not line.green_on_positive else ' income_budget'

            if line.hide_in_budget:
                final_result_table += self._get_unaffected_lines(line, financial_report, currency_table,
                                                                 daterange_list, analytic_account_id)
                continue

            vals = {
                'id': line.id,
                'name': line.name,
                'level': line.level,
                'unfoldable': len(domain_ids) > 1 and line.show_domain != 'always',
                'columns': [{'name': 0} for i in range(column_number)] if not line.domain else [],
                'positive': line.green_on_positive,
            }

            if line.action_id:
                vals['action_id'] = line.action_id.id
            if line.financial_report_id:
                vals['total_id'] = str(line.id)
            if line.formulas and not line.domain:
                vals['formulas'] = line.formulas.split('=')[1].replace('.balance', '')
            if line.code and not line.domain:
                vals['code'] = line.code

            lines += [vals]
            groupby = line.groupby or 'aml'

            if line.domain:
                edit_domain = line.domain.replace('account_id.', '')
                domain_ids = sorted(AccountAccount.search(ast.literal_eval(edit_domain)).ids)
                balance_sheet_dict = _get_balance_sheet_value(line, financial_report, currency_table,
                                                              daterange_list, analytic_account_id)

            for domain_id in domain_ids:
                name = str(line._get_gb_name(domain_id))
                columns = []
                actual_total = 0
                budget_total = 0

                budget_lines = crossovered_budget.crossovered_budget_line.filtered(
                    lambda x: domain_id in x.general_budget_id.account_ids.ids).sorted(lambda x: x.date_from)

                if not is_profit_budget:  # BALANCE SHEET
                    practical_amount_array = balance_sheet_dict.get(domain_id, empty)

                    for index, daterange in enumerate(daterange_list):
                        range_lines = budget_lines.filtered(lambda x: x.date_to == daterange[1])

                        practical_amount = practical_amount_array[index]
                        planned_amount_entry = range_lines[0].planned_amount_entry if range_lines else 0

                        result = self._get_budget_value(practical_amount, planned_amount_entry, True)
                        columns.extend(result)
                else:  # PROFIT & LOSS
                    if daterange_list:
                        for daterange in daterange_list:
                            range_lines = budget_lines.filtered(lambda x: x.date_from >= daterange[0]
                                                                          and x.date_to <= daterange[1])

                            practical_amount = sum([i.practical_amount for i in range_lines])
                            planned_amount_entry = sum([i.planned_amount_entry for i in range_lines])

                            actual_total += practical_amount
                            budget_total += planned_amount_entry

                            result = self._get_budget_value(practical_amount, planned_amount_entry, line.green_on_positive)
                            columns.extend(result)
                    else:
                        # Whole Budget, will show only Total column
                        actual_total = sum([i.practical_amount for i in budget_lines])
                        budget_total = sum([i.planned_amount_entry for i in budget_lines])

                    # Add extra Total column, only for P&L
                    result = self._get_budget_value(actual_total, budget_total, line.green_on_positive)
                    columns.extend(result)

                if not columns:
                    columns = empty

                vals = {
                    'id': domain_id,
                    'account_id': domain_id,
                    'name': name and len(name) >= 45 and name[0:40] + '...' or name,
                    'level': 4,
                    'parent_id': line.id,
                    'columns': [{'name': format_number(i),
                                 'color_class': class_name if i > 100 else ''} for i in columns],
                    'caret_options': groupby == 'account_id' and 'account.account' or groupby,
                    'positive': line.green_on_positive,
                }
                lines.append(vals)

            if domain_ids:  # total-line of sub lines => don't need formula
                lines.append({
                    'id': 'total_' + str(line.id),
                    'total_id': str(line.id),
                    'code': line.code,
                    'name': _('Total') + ' ' + line.name,
                    'class': 'o_account_reports_domain_total',
                    'columns': [{'name': 0} for i in range(column_number)],
                    'positive': line.green_on_positive,
                })

            if len(lines) == 1:
                new_lines = self._get_dict_lines(line.children_ids, column_number, crossovered_budget, daterange_list,
                                                 financial_report, currency_table, is_profit_budget)

                if new_lines and line.level > 0 and line.formulas:
                    divided_lines = _divide_line(lines[0], column_number, line)
                    result = [divided_lines[0]] + new_lines + [divided_lines[1]]
                else:
                    result = []
                    if line.level > 0:
                        result += lines
                    result += new_lines
                    if line.level <= 0:
                        result += lines
            else:
                result = lines
            final_result_table += result

        return final_result_table

    @api.multi
    def get_html(self, options, line_id=None, additional_context=None):
        if additional_context is None:
            additional_context = {}

        crossovered_budget = self._get_crossovered_budget_obj()
        is_profit_budget = True if crossovered_budget.budget_type == 'profit' else False
        financial_report = self.env.ref('account_reports.account_financial_report_profitandloss0') \
            if is_profit_budget else self.env.ref('account_reports.account_financial_report_balancesheet0')
        currency_table = financial_report._get_currency_table()

        # get lines, put it here because we need to create the budget before _get_lines.
        daterange_list = self._get_daterange_list(options, crossovered_budget)
        column_number = (len(daterange_list) + 1) * 4 if is_profit_budget else (len(daterange_list)) * 4

        # # get lines
        lines = self._get_dict_lines(financial_report.line_ids, column_number, crossovered_budget, daterange_list,
                                     financial_report, currency_table, is_profit_budget)

        # add more options
        options.update({
            'column_number': column_number,
            'crossovered_budget': crossovered_budget,
            'crossovered_budget_id': crossovered_budget.id,
            'lines': lines,
            'daterange_list': daterange_list,
            'groupby': options['groupby']
        })

        additional_context.update({
            'crossovered_budget': crossovered_budget,
            'currency_id': self.env.user.company_id.currency_id
        })

        return super(BudgetReport, self).get_html(options, line_id=line_id,
                                                 additional_context=additional_context)

    def get_xlsx(self, options, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Sheet 1')
        budget = self.env['crossovered.budget'].browse(options['crossovered_budget_id'])

        # Styles
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10})
        header_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'border': 1})
        header_center_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True,
                                                   'align': 'center', 'valign': 'vcenter', 'border': 1})
        header_style_row = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True})
        subtotal_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'bottom': 1})
        formula_total_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'bottom': 6})

        default_style.set_locked(False)
        default_style.set_num_format('#,##0.00')
        subtotal_style.set_num_format('#,##0.00')
        formula_total_style.set_num_format('#,##0.00')

        # Set the first column width to 50
        sheet.set_column(0, 0, 50)
        sheet.set_column(1, 80, 15)

        # Write the headers
        headers = self._get_columns_name(options, export=True, budget=budget)
        cell_range = utility.xl_range(0, 0, 1, 0)
        sheet.merge_range(cell_range, 'Account', header_center_style)

        row = 0
        col = 1
        for header in headers:
            col_span = header.get('colspan', 1)
            if col_span == 1:
                continue
            cell_range = utility.xl_range(row, col, row, col + col_span - 1)
            sheet.merge_range(cell_range,  header['name'], header_center_style)
            col += col_span

        row = 1
        col = 1
        for i in range(len(headers)-1):
            sheet.write(row, col, 'Actual', header_style)
            sheet.write(row, col+1, 'Budget', header_style)
            sheet.write(row, col+2, 'Variance', header_style)
            sheet.write(row, col+3, '% of Budget', header_style)
            col += 4

        # Start from the first cell. Rows and columns are zero indexed,
        data = options.get('data', [])
        row = 2

        # Iterate over the data and write it out row by row.
        for row_dict in data:
            col = 0

            style = default_style if row_dict['parent_id'] else header_style_row
            if row_dict['total_id'] and not row_dict['formulas']:
                style = subtotal_style
            elif row_dict['formulas']:
                style = formula_total_style

            row_data = row_dict['data']
            sheet.write_row(row, col, row_data, style)

            row += 2 if row_dict['formulas'] else 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    # HELPER FUNCTION
    def _get_daterange_list(self, options, budget):
        date_from = budget.date_from
        date_to = budget.date_to
        filter_groupby = options['groupby']['filter']
        daterange_list = []

        if filter_groupby == 'Monthly':
            daterange_list = get_list_period_by_type(date_from, date_to, "BY_MONTH")
        elif filter_groupby == 'Quarterly':
            daterange_list = get_list_period_by_type(date_from, date_to, "BY_QUARTER")
        elif filter_groupby == 'Yearly':
            daterange_list = get_list_period_by_type(date_from, date_to, "BY_YEAR")
        elif filter_groupby == 'Whole Budget' and budget.budget_type == 'balance':
            daterange_list = [(False, date_to)]

        return daterange_list

    def _get_crossovered_budget_obj(self):
        crossovered_budget_id = self.env.context.get('crossovered_budget_id', False)
        params = self.env.context.get('params', False)

        if not crossovered_budget_id and params and params.get('action', False):
            action_obj = self.env['ir.actions.client'].browse(params['action'])
            crossovered_budget_id = action_obj.params.get('crossovered_budget_id', False)

        crossovered_budget = self.env['crossovered.budget'].browse(crossovered_budget_id)

        return crossovered_budget

    @api.multi
    def _get_unaffected_lines(self, children_lines, financial_report, currency_table,
                              daterange_list, analytic_account_id):
        """
        Special function to get lines for Unaffected Earnings in Balance Sheet report
        :return: dictionary of lines to display in report
        """
        result = []
        for line in children_lines:
            columns = []
            line_dict = _get_balance_sheet_value(line, financial_report, currency_table,
                                                 daterange_list, analytic_account_id)
            line_array = line_dict['line']

            for practical_amount in line_array:
                columns.extend([
                    {'name': format_number(practical_amount)},
                    {'name': '0.00'},
                    {'name': format_number(practical_amount)},
                    {'name': '0.00'}
                ])

            vals = {
                'id': line.id,
                'name': line.name,
                'code': line.code,
                'level': line.level,
                'positive': line.green_on_positive,
                'columns': columns
            }

            lines = [vals]

            if line.children_ids:
                new_lines = self._get_unaffected_lines(line.children_ids, financial_report, currency_table,
                                                       daterange_list, analytic_account_id)
                lines += new_lines
            result += lines
        return result

    @api.model
    def _get_budget_value(self, practical_amount, planned_amount, green_on_positive):
        practical_amount = practical_amount * -1 if not green_on_positive and practical_amount else practical_amount

        return [practical_amount, planned_amount,
                practical_amount - planned_amount,
                (practical_amount / planned_amount * 100 + 0) if planned_amount else 0]

