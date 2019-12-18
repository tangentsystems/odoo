# -*- coding: utf-8 -*-

from odoo import api, fields, models


class DialogEntityType(models.Model):
    _name = 'dialog.entity.type'
    _inherit = 'dialog.base'
    _description = 'DialogFlow Entity Type'

    dfid = fields.Char(
        'DFID',
        help='ID from DialogFlow',
        readonly=True
    )
    name = fields.Char(
        required=True
    )
    kind = fields.Selection([
        ('KIND_MAP', 'KIND_MAP'),
        ('KIND_LIST', 'KIND_LIST'),
        ('KIND_UNSPECIFIED', 'KIND_UNSPECIFIED'),
    ], default='KIND_MAP')
    entity_ids = fields.One2many(
        'dialog.entity',
        'entity_type_id',
        'Entities'
    )

    def _get_id_str(self, full_name):
        return full_name.split('/')[-1]

    @api.model
    def get_list_df_entity_type(self):
        '''
        Get all entity types from Dialogflow and create them immediately
        '''
        # Get all entity types protobuf
        entity_types = self.list_entity_types()
        for entity_type in entity_types:
            entity_type_dict = self._convert_message_to_dict(entity_type)
            entities = entity_type_dict.get('entities', [])
            lst_entity = []
            for entity in entities:
                lst_entity += [(0, 0, {
                    'value': entity.get('value'),
                    'synonyms': ','.join(entity.get('synonyms', []))
                })]
            value = {
                'dfid': self._get_id_str(entity_type_dict.get('name')),
                'name': entity_type_dict.get('displayName'),
                'entity_ids': lst_entity,
            }
            self.create(value)
        return True

    @api.multi
    def name_get(self):
        '''
        Add '@' into name. Make it familiar with Dialogflow
        '''
        result = []
        for record in self:
            complete_name = '@' + record.name
            result.append((record.id, complete_name))
        return result
