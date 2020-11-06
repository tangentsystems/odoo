# -*- coding: utf-8 -*-
{
    'name': 'TS: SOL Parent Task',
    'summary': 'Tangent Systems LLC: Parent Task Development',
    'description': """
ID=2006993
    """,
    'license': 'OEEL-1',
    'author': 'Odoo Inc',
    'version': '0.1',
    'depends': ['project', 'sale_management', 'account_accountant', 'sale_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/product_views.xml',
        'views/project_views.xml',
        'views/res_partner_views.xml'
    ],
}
