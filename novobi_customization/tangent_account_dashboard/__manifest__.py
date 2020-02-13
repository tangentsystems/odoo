# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

{
    'name': "Tangent Account Dashboard",

    'summary': """""",

    'description': """
    """,

    'author': 'Novobi',
    'website': 'https://novobi.com',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '1.0',
    'license': 'OPL-1',
    # any module necessary for this one to work correctly
    'depends': [
        'l10n_us_accounting',
        'account_dashboard'
    ],
    'data': [
        'views/assets.xml',
        'views/account_dashboard_views.xml',
        'data/tangent_journal_data.xml'
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False,
}
