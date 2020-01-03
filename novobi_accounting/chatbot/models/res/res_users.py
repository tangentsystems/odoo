# -*- coding: utf-8 -*-

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    odoobot_state = fields.Selection(
        selection_add=[('smart_bot', 'Smart Bot')]
    )
    session_id = fields.Char('Session')
