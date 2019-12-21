# -*- coding: utf-8 -*-

import dialogflow_v2beta1 as dialogflow
from dialogflow_v2beta1.proto import intent_pb2
from google.oauth2 import service_account
from google.protobuf.json_format import MessageToDict, MessageToJson, ParseDict
from odoo import models
from odoo.tools import config
import re
import logging
_logger = logging.getLogger(__name__)

DF_PROJECT_ID = config.get("df_project", False)
DF_ACCOUNT_FILE = config.get("df_account_file", False)


class DialogBase(models.AbstractModel):
    _name = 'dialog.base'
    _description = 'DialogFlow Base'

    # =========================================================================
    #  HELPERS
    # =========================================================================
    def _get_credentials(self):
        return service_account.\
            Credentials.from_service_account_file(DF_ACCOUNT_FILE)

    def _get_session_client(self):
        session_id = self.env.user.session_id or ''
        credentials = self._get_credentials()
        client = dialogflow.SessionsClient(credentials=credentials)
        session = client.session_path(DF_PROJECT_ID, session_id)
        return client, session

    def _convert_message_to_dict(self, protobuf_obj):
        return MessageToDict(protobuf_obj)

    def _convert_message_to_json(self, protobuf_obj):
        return MessageToJson(protobuf_obj)

    def camel_to_snake(s):
        """
        Convert style camelCase to snake_case
        """
        subbed = re.compile(r'(.)([A-Z][a-z]+)').sub(r'\1_\2', s)
        return re.compile('([a-z0-9])([A-Z])').sub(r'\1_\2', subbed).lower()

    def snakeToCamel(s):
        """
        Convert style snake_case to camelCase
        """
        lst_s = s.split('_')
        return lst_s[0] + ''.join(word.capitalize() for word in lst_s[1:])

    # =========================================================================
    # DETECTING INTENTS
    # =========================================================================
    def detect_intent_text(self, text, language_code='en'):
        """
        Returns the result of detect intent with texts as inputs.

        Using the same `session_id` between requests allows continuation
        of the conversation.
        """
        client, session = self._get_session_client()
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)
        query_input = dialogflow.types.QueryInput(text=text_input)

        response = client.detect_intent(
            session=session, query_input=query_input)

        return response

    # =========================================================================
    # MANAGING INTENTS
    # =========================================================================
    def list_intents(self, language_code='en'):
        """
        Returns the list of all intents in the specified agent.
        Args:
        language_code (str): Optional. The language to list training phrases, parameters and rich
                messages for. If not specified, the agent's default language is used.
                [More than a dozen
                languages](https://dialogflow.com/docs/reference/language) are supported.
                Note: languages must be enabled in the agent before they can be used.
        Returns:
            A :class:`~google.gax.PageIterator` instance. By default, this
            is an iterable of :class:`~google.cloud.dialogflow_v2.types.Intent` instances.
            This object can also be configured to iterate over the pages
            of the response through the `options` parameter.
        """
        credentials = self._get_credentials()
        intents_client = dialogflow.IntentsClient(credentials=credentials)
        parent = intents_client.project_agent_path(DF_PROJECT_ID)
        response = intents_client.list_intents(parent, intent_view='INTENT_VIEW_FULL', language_code=language_code)

        _logger.info('Listed Intents: {}'.format(response))

        return response

    def get_intent(self, intent_id, language_code='en'):
        """
        Retrieves the specified intent.
        Args:
            intent_id (str): Required. The name of the intent.
                Format: ``projects/<Project ID>/agent/intents/<Intent ID>``.
            language_code (str): Optional. The language to retrieve training phrases, parameters and rich
                messages for. If not specified, the agent's default language is used.
                [More than a dozen
                languages](https://dialogflow.com/docs/reference/language) are supported.
                Note: languages must be enabled in the agent, before they can be used.
        Returns:
            A :class:`~google.cloud.dialogflow_v2.types.Intent` instance.
        """
        credentials = self._get_credentials()
        intents_client = dialogflow.IntentsClient(credentials=credentials)
        response = intents_client.intent_path(DF_PROJECT_ID, intent_id, language_code=language_code)
        _logger.info('Gotten Intent: \n{}'.format(response))
        return response

    def create_intent(self, value_dict):
        """
        Create an intent of the given intent type.
        Args:
            value_dict (dict): Required. Dictionary of intent values
            {
                'display_name': ...,
                'training_phrases': ...,
                'messages': ...,
            }
        Returns:
            A :class:`~google.cloud.dialogflow_v2.types.Intent` instance.
        """
        credentials = self._get_credentials()
        intents_client = dialogflow.IntentsClient(credentials=credentials)

        # Prepare values
        display_name = value_dict.get('display_name')
        training_phrases = value_dict.get('training_phrases')
        messages = value_dict.get('messages')
        parameters = value_dict.get('parameters')

        intent = dialogflow.types.Intent(
            display_name=display_name,
            training_phrases=training_phrases,
            parameters=parameters,
            messages=messages)

        parent = intents_client.project_agent_path(DF_PROJECT_ID)
        response = intents_client.create_intent(parent, intent)

        _logger.info('Intent created: %s' % display_name)

        return response

    def update_intent(self, intent_dict, language_code='en'):
        """
        Updates the specified intent.
        Args:
            intent_dict (dict): Required.
                Format: ``projects/<Project ID>/agent/intents/<Intent ID>``.
                If a dict is provided, it must be of the same form as the protobuf
                message :class:`~google.cloud.dialogflow_v2.types.Intent`
            language_code (str): Optional. The language of training phrases, parameters and rich messages
                defined in ``intent``. If not specified, the agent's default language is
                used. [More than a dozen
                languages](https://dialogflow.com/docs/reference/language) are supported.
                Note: languages must be enabled in the agent, before they can be used.
        Returns:
            A :class:`~google.cloud.dialogflow_v2.types.Intent` instance.
        """
        credentials = self._get_credentials()
        intents_client = dialogflow.IntentsClient(credentials=credentials)
        # update parent into name
        parent = intents_client.project_agent_path(DF_PROJECT_ID)
        intent_dict['name'] = \
            parent + '/intents/' + intent_dict.get('name', '')
        # convert to pb2 message
        intent_tmp = intent_pb2.Intent()

        intent_message = ParseDict(js_dict=intent_dict, message=intent_tmp)

        response = intents_client.update_intent(
            intent=intent_message,
            language_code=language_code,
            intent_view='INTENT_VIEW_FULL'
        )
        _logger.info('Updated Intent: \n{}'.format(response))
        return response

    def delete_intent(self, intent_id):
        """Delete intent with the given intent type and intent value."""
        credentials = self._get_credentials()
        intents_client = dialogflow.IntentsClient(credentials=credentials)

        intent_path = intents_client.intent_path(DF_PROJECT_ID, intent_id)

        response = intents_client.delete_intent(intent_path)
        _logger.info('Deleted Intent: \n{}'.format(response))
        return response

    def batch_action_intents(self, intents, action, language_code='en'):
        """
        Updates/Creates/Deletes multiple intents in the specified agent.
        Args:
            intents (list): Required. The list of intents dictionary.
            action (create/update/delete): Required.
            language_code (str): Optional. The language of training phrases, parameters and rich messages
                    defined in ``intents``. If not specified, the agent's default language is
                    used. [More than a dozen
                    languages](https://dialogflow.com/docs/reference/language) are supported.
                    Note: languages must be enabled in the agent, before they can be used.
        """
        credentials = self._get_credentials()
        intents_client = dialogflow.IntentsClient(credentials=credentials)
        parent = intents_client.project_agent_path(DF_PROJECT_ID)
        if action in ['update', 'create']:
            response = intents_client.batch_update_intents(
                parent=parent,
                intent_batch_inline=intents,
                language_code=language_code
            )
            _logger.info('Updated/Created Intents: \n{}'.format(response))

        elif action == 'delete':
            response = intents_client.batch_delete_intents(
                parent=parent,
                intents=intents,
                language_code=language_code
            )
            _logger.info('Deleted Intents: \n{}'.format(response))

        else:
            raise ("Invalid action '{}'".format(action))
        return response

    # =========================================================================
    # MANAGING ENTITY TYPES
    # =========================================================================
    def list_entity_types(self):
        credentials = self._get_credentials()
        entity_types_client = dialogflow.EntityTypesClient(credentials=credentials)

        parent = entity_types_client.project_agent_path(DF_PROJECT_ID)

        response = entity_types_client.list_entity_types(parent)

        _logger.info('Listed Entity Types: {}'.format(response))
        return response

    def create_entity_type(display_name, kind):
        """Create an entity type with the given display name."""
        entity_types_client = dialogflow.EntityTypesClient()

        parent = entity_types_client.project_agent_path(DF_PROJECT_ID)
        entity_type = dialogflow.types.EntityType(
            display_name=display_name, kind=kind)

        response = entity_types_client.create_entity_type(parent, entity_type)

        _logger.info('Entity type created: \n{}'.format(response))
        return response

    # TODO: Implement Updating, Listing

    def delete_entity_type(entity_type_id):
        """Delete entity type with the given entity type name."""
        entity_types_client = dialogflow.EntityTypesClient()

        entity_type_path = entity_types_client.entity_type_path(
            DF_PROJECT_ID, entity_type_id)

        entity_types_client.delete_entity_type(entity_type_path)

    # =========================================================================
    # MANAGING ENTITIES
    # =========================================================================
    def create_entity(entity_type_id, entity_value, synonyms):
        """Create an entity of the given entity type."""
        entity_types_client = dialogflow.EntityTypesClient()

        # Note: synonyms must be exactly [entity_value] if the
        # entity_type's kind is KIND_LIST
        synonyms = synonyms or [entity_value]

        entity_type_path = entity_types_client.entity_type_path(
            DF_PROJECT_ID, entity_type_id)

        entity = dialogflow.types.EntityType.Entity()
        entity.value = entity_value
        entity.synonyms.extend(synonyms)

        response = entity_types_client.batch_create_entities(
            entity_type_path, [entity])

        _logger.info('Entity created: {}'.format(response))
        return response

    # TODO: Implement Updating, Listing

    def delete_entity(entity_type_id, entity_value):
        """Delete entity with the given entity type and entity value."""
        entity_types_client = dialogflow.EntityTypesClient()

        entity_type_path = entity_types_client.entity_type_path(
            DF_PROJECT_ID, entity_type_id)

        entity_types_client.batch_delete_entities(
            entity_type_path, [entity_value])

    # =========================================================================
    # MANAGING CONTEXT
    # =========================================================================
    def delete_all_contexts(self):
        """
        Deletes all active contexts in the specified session.
        """
        credentials = self._get_credentials()
        context_client = dialogflow.ContextsClient(credentials=credentials)
        session = self.env.user.session_id or ''
        parent = context_client.session_path(DF_PROJECT_ID, session)
        response = context_client.delete_all_contexts(parent)
        return response
