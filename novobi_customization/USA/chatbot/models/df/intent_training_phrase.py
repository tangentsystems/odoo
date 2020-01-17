# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IntentTrainingPhrase(models.Model):
    _name = 'intent.training.phrase'
    _description = 'DialogFlow Training Phrase'

    type = fields.Selection([
        ('EXAMPLE', 'EXAMPLE'),
        ('TYPE_UNSPECIFIED', 'TYPE_UNSPECIFIED'),
        ('TEMPLATE  ', 'TEMPLATE'),
    ], default='EXAMPLE')
    full_text = fields.Char('Full Text')
    dialog_intent_id = fields.Many2one(
        'dialog.intent',
        'Intent',
        ondelete='cascade'
    )
    parameter_ids = fields.One2many(
        'intent.parameter',
        'training_phrase_id',
        'Parameters'
    )
    training_part_ids = fields.One2many(
        'intent.training.part',
        'training_phrase_id',
        'Parts'
    )

    @api.multi
    def parse_df_style(self):
        '''
        Convert Odoo fields to Dialogflow style
        Returns:
            lst_value (list): List of Dialogflow intent Training Phrases values
        '''
        lst_value = []
        for phrase in self:
            part_ids = phrase.training_part_ids or False
            parts = part_ids and part_ids.parse_df_style() or []
            value = {
                'parts': parts,
                'type': phrase.type,
            }
            lst_value.append(value)
        return lst_value


class IntentTrainingPart(models.Model):
    _name = 'intent.training.part'
    _description = 'DialogFlow Training Parts'

    entity_type = fields.Char('Entity Type')  # TODO: Many2one with entity.type
    alias = fields.Char()
    text = fields.Char()
    training_phrase_id = fields.Many2one(
        'intent.training.phrase',
        'Training Phrase',
        ondelete='cascade'
    )

    @api.multi
    def parse_df_style(self):
        '''
        Convert Odoo fields to Dialogflow style
        Returns:
            lst_value (list): List of Dialogflow intent Training Parts values
        '''
        lst_value = []
        for part in self:
            value = {
                'entity_type': part.entity_type or '',
                'alias': part.alias or '',
                'text': part.text or '',
            }
            lst_value.append(value)
        return lst_value


class IntentParameter(models.Model):
    _name = 'intent.parameter'
    _description = 'DialogFlow Intent Parameter'

    name = fields.Char('Display name')
    value = fields.Char('Value')
    entity_type_display_name = fields.Char('Entity type display name')
    training_phrase_id = fields.Many2one(
        'intent.training.phrase',
        'Training Phrase',
        ondelete='cascade'
    )

    @api.multi
    def parse_df_style(self):
        '''
        Convert Odoo fields to Dialogflow style
        Returns:
            lst_value (list): List of Dialogflow intent parameter values
        '''
        lst_value = []
        for param in self:
            value = {
                'display_name': param.name or '',
                'entity_type_display_name': param.entity_type_display_name or '',
                'value': param.value or '',
            }
            lst_value.append(value)
        return lst_value
