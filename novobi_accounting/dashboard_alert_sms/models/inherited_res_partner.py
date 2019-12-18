# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, modules, tools, _


class InheritedResPartner(models.Model):
    _inherit = 'res.partner'

    # slack_real_name = fields.Char('Slack Real Name')
    # slack_id = fields.Char(compute='_compute_slack_id', default='')
    #
    # ########################################################
    # # COMPUTED FUNCTION
    # ########################################################
    # @api.depends('slack_real_name')
    # def _compute_slack_id(self):
    #     for user in self:
    #         slack_connector = SlackConnector.getInstance()
    #
    #         api_call = slack_connector.slack_client.api_call('users.list')
    #         if api_call.get('ok'):
    #             # retrieve all users so we can find our bot
    #             users = api_call.get('members')
    #             for slack_user in users:
    #                 if 'real_name' in slack_user and slack_user.get('real_name') == user.slack_real_name:
    #                     user.slack_id = slack_user.get('id')
