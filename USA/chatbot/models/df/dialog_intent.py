# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class DialogIntent(models.Model):
    """
    - This model stores essential fields
        from https://dialogflow.com/docs/reference/api-v2/rest/v2/projects.agent.intents
    - Intent structure:
        {
            "name": string,
            "displayName": string,
            "trainingPhrases": [
                { object(TrainingPhrase) }
            ],
            "messages": [
                { object(Message) }
            ],
        }
    """
    _name = 'dialog.intent'
    _inherit = 'dialog.base'
    _description = 'DialogFlow Intent'

    dfid = fields.Char('DFID')
    name = fields.Char()
    training_phrase_ids = fields.One2many(
        'intent.training.phrase',
        'dialog_intent_id',
        'Training phrases'
    )
    response_ids = fields.One2many(
        'intent.response',
        'dialog_intent_id',
        'Responses'
    )

    def _get_id_str(self, full_name):
        return full_name.split('/')[-1]

    @api.multi
    def parse_df_style(self):
        '''
        Convert Odoo fields to Dialogflow style
        Returns:
            lst_value (list): List of Dialogflow intent values
        '''
        lst_value = []
        for intent in self:
            # Parse training phrases
            phrases = intent.training_phrase_ids or False
            training_phrases = phrases and phrases.parse_df_style() or []
            # Parse messages
            responses = intent.response_ids or False
            messages = responses and responses.parse_df_style() or []

            value = {
                'display_name': intent.name,
                'training_phrases': training_phrases,
                'messages': messages
            }
            if intent.dfid:
                value['name'] = intent.dfid
            lst_value.append(value)
        return lst_value

    @api.model
    def get_list_df_intents(self):
        '''
        Get all intents from Dialogflow and create them immediately
        '''
        # Get all intents protobuf
        intents = self.list_intents()
        for intent in intents:
            intent_dict = self._convert_message_to_dict(intent)

            # Prepare intent parameters
            parameters = intent_dict.get('parameters', [])
            lst_parameters = []
            if parameters:
                for parameter in parameters:
                    # Add tuple (0, 0, value) to create
                    lst_parameters += [(0, 0, {
                        'entity_type_display_name': parameter.get('entityTypeDisplayName'),
                        'value': parameter.get('value'),
                        'name': parameter.get('displayName'),
                    })]

            # Prepare intent training phrases
            training_phrases = intent_dict.get('trainingPhrases', [])
            lst_training_phrases = []
            if training_phrases:
                for phrase in training_phrases:
                    lst_training_parts = []
                    parts = phrase.get('parts', [])
                    full_text = ''
                    if parts:
                        for part in parts:
                            text = part.get('text')
                            full_text += text
                            # Add tuple (0, 0, value) to create
                            lst_training_parts += [(0, 0, {
                                'entity_type': part.get('entityType'),
                                'alias': part.get('alias'),
                                'text': text,
                            })]
                    # Add tuple (0, 0, value) to create
                    lst_training_phrases += [(0, 0, {
                        'full_text': full_text,
                        'training_part_ids': lst_training_parts,
                        'parameter_ids': lst_parameters,
                    })]

            # Prepare intent response
            responses = intent_dict.get('messages', [])
            lst_response = []
            if responses:
                # We only need to get text responses from Dialogflow
                text_responses = list(map(
                    lambda xx: xx.get('text'),
                    map(lambda x: x.get('text'), responses)
                ))
                if text_responses and isinstance(text_responses, list):
                    valid_text_responses = text_responses[0]
                    for text_response in valid_text_responses:
                        lst_response += [(0, 0, {
                            'name': text_response
                        })]
            # Prepare intent value
            full_name = intent_dict.get('name')
            value = {
                'dfid': self._get_id_str(full_name),
                'name': intent_dict.get('displayName'),
                'training_phrase_ids': lst_training_phrases,
                'response_ids': lst_response,
            }
            # Create single intent and related components (phrases, responses)
            self.create(value)
        return True

    @api.multi
    def create_df_intent(self, value):
        self.ensure_one()
        return True

    @api.multi
    def button_update_intent(self):
        for intent in self:
            lst_value = intent.parse_df_style()
            if not lst_value:
                continue
            # lst_value should be a record (not record set) so...
            value = lst_value[0]
            if intent.dfid:
                # Update Dialogflow intent
                intent.update_intent(value)
            else:
                # Create Dialogflow intent
                response = intent.create_intent(value)
                intent.dfid = self._get_id_str(response.name)
        return True

    @api.multi
    def button_delete_intent(self):
        for intent in self:
            if intent.dfid:
                # Delete Dialogflow intent
                intent.delete_intent(intent_id=intent.dfid)
                intent.dfid = False
                continue
            raise ("This intent <%s> has been deleted or hasn't been created yet" % intent.name)
        return True
