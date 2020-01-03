# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AlertInfoCreator(models.TransientModel):
    _name = 'kpi.list'

    # store message to show in a popup confirmation window
    kpi_ids = fields.Many2many('alert.info')

    def create_kpi(self):
        """
        write the action for button "YES"
        :return:
        """
        print('create_kpi')
        return self.env.context.get('action_confirm')
