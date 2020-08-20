# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super(Http, self).session_info()
        self.env.user.session_id = res.get('session_id', '')
        return res
