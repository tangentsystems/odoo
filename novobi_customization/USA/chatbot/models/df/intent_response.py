# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IntentResponse(models.Model):
    _name = 'intent.response'
    _description = 'DialogFlow Intent Response'

    name = fields.Text('Text')
    dialog_intent_id = fields.Many2one(
        'dialog.intent',
        'Intent'
    )

    @api.multi
    def parse_df_style(self):
        '''
        Convert Odoo fields to Dialogflow style
        Returns:
            List of Dialogflow intent response values
        '''
        return [{
            'text': {
                'text': self.mapped('name')
            }
        }]
