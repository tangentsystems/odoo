# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

{
    "name": "Ribbon",
    "summary": "Ribbon for Odoo 12.0",
    "version": "1",
    "author": "Novobi",
    "website": "https://www.novobi.com/",
    "description": """""",
    "depends": [
        'web',
    ],
    "data": [
        'views/assets.xml',
    ],
    "qweb": ['static/src/xml/*.xml'],
    "application": False,
    "installable": True,
    "auto_install": False,
}
