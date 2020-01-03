# -*- coding: utf-8 -*-

from . import controllers
from . import models


from odoo import api, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    _logger.info("=======Run post init hook======")
    _list_intents(cr, registry)


def _list_intents(cr, registry):
    """
    This hook is used to create all intents from Dialogflow
        when module chatbot is installed.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    intent_env = env['dialog.intent']
    intent = intent_env.search([], limit=1)
    if not intent:
        intent_env.get_list_df_intents()
