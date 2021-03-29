# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Accounting Budget Advanced',
    'summary': 'Accounting Budget Advanced',
    'author': 'Novobi',
    'website': 'http://www.odoo-accounting.com',
    'category': 'Accounting',
    'version': '1.0',
    'license': 'OPL-1',
    'depends': [
        'account_accountant',
        'l10n_generic_coa',
        'account_budget',
        'account_reports',
    ],

    'data': [
        # 'data/account_data.xml',
        'data/account_financial_report_data.xml',

        'views/assets.xml',
        'views/account_financial_report_view.xml',
        'views/budget_entry_screen.xml',
        'views/budget_report_screen.xml',
        'views/account_budget_views.xml',

        'wizard/account_budget_wizard_view.xml',
        'wizard/consolidated_budget_wizard_views.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
}
