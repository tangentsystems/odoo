# -*- coding: utf-8 -*-

from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def im_search(self, name, limit=20):
        res = super(ResPartner, self).im_search(name=name, limit=limit)
        # Show chatbot
        res += [
            {
                'user_id': self.env.ref('base.user_root').id,
                'id': self.env.ref('base.partner_root').id,
                'im_status': 'online',
                'name': 'OdooBot'
            }
        ]
        return res
