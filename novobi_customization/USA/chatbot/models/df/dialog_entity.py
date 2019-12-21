# -*- coding: utf-8 -*-

from odoo import api, fields, models


class DialogEntity(models.Model):
    _name = 'dialog.entity'
    _description = 'DialogFlow Entities'
    _rec_name = 'value'

    value = fields.Char(
        'Value',
        required=True
    )
    synonyms = fields.Text('Synonyms')
    entity_type_id = fields.Many2one(
        'dialog.entity.type',
        'Entity type',
        ondelete='cascade'
    )

    @api.multi
    def parse_df_style(self):
        '''
        Convert Odoo fields to Dialogflow style
        Returns:
            List of Dialogflow entity values
        '''
        lst_value = []
        for entity in self:
            value = {
                'value': entity.value or '',
                'type': entity.synonyms or '',
            }
            lst_value.append(value)
        return lst_value
