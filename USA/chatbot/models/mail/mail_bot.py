# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

# from random import choice
from odoo import api, models


class MailBot(models.AbstractModel):
    _inherit = 'mail.bot'

    @api.model
    def _get_answer(self, record, body, values, command=False):
        user = self.env.user
        odoobot_state = user.odoobot_state
        if self._is_bot_in_private_channel(record):
            if odoobot_state == 'smart_bot':
                # Create history for the next action
                history = self.env['dialog.history'].create({
                    'request': body,
                    'channel_id': record.id,
                })
                history.detect_intent(text=body)
                return history.response

        return super(MailBot, self)._get_answer(record=record, body=body,
                                                values=values, command=command)
