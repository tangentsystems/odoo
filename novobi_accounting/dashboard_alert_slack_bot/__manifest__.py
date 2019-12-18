# -*- coding: utf-8 -*-
{
    'name': 'Account - Slack Bot',
    'summary': '',
    'author': 'Novobi',
    'website': 'https://novobi.com',
    'category': 'Accounting',
    'version': '1.0',
    'depends': [
        'dashboard_alert'
    ],

    'data': [
        'data/alert_channel_data.xml',

        'views/inherited_res_partner_views.xml',
        'views/inherited_res_config_setting_views.xml'
    ],
    'qweb': ['static/src/xml/*.xml'],
}
