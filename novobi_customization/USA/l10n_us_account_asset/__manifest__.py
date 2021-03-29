# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

{
    'name': 'l10n_us_account_asset',
    'summary': 'US Accounting Asset',
    'author': 'Novobi',
    'website': 'https://novobi.com',
    'category': 'Accounting',
    'version': '1.0',
    'license': 'OPL-1',
    'depends': [
        'account_accountant',
        'l10n_us_accounting',
        'account_asset',
    ],

    'data': [
        'views/res_config_settings_views.xml',
        'views/account_asset_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
