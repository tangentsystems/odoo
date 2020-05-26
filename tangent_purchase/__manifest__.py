# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tangent: Purchase',
    'summary': 'Tangent: Purchase',
    'category': 'Purchase',
    "author": "Novobi",
    "website": "https://www.novobi.com/",
    'depends': [
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/purchase_order_views.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    "application": False,
    "installable": True,
}
