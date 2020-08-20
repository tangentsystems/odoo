# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tangent: Sales',
    'summary': 'Tangent: Sales',
    'category': 'Sales',
    "author": "Novobi",
    "website": "https://www.novobi.com/",
    'depends': [
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/sale_views.xml',
        'wizard/review_sale_order_views.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    "application": False,
    "installable": True,
}
