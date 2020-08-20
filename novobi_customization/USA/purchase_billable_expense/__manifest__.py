# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Billable Expense - assigned to customer from Purchase Order',
    'summary': 'Accounting: Billable Expense for Purchase',
    'author': 'Novobi',
    'website': 'http://www.odoo-accounting.com',
    'category': 'Accounting',
    'version': '1.0',
    'license': 'OPL-1',
    'depends': [
        'purchase',
        'account_billable_expense',
    ],

    'data': [
        'views/purchase_order_view.xml',
        'report/billable_expense_report.xml',
    ],
}
