# -*- coding: utf-8 -*-

{
    'name': 'ChatBot',
    'version': '12.0.1.0.0',
    'category': 'Discuss',
    'summary': 'Add Smart OdooBot in discussions',
    'author': 'Novobi',
    'website': 'https://www.novobi.com',
    'depends': ['mail_bot'],
    'data': [

        # ============================== VIEWS ================================
        'views/df/dialog_history_views.xml',
        'views/df/dialog_intent_views.xml',
        'views/df/dialog_entity_type_views.xml',
        'views/res/res_users_views.xml',
        'views/ir/ir_model_views.xml',
        'views/assets.xml',

        # ============================== SECURITY =============================
        'security/ir.model.access.csv',

        # ============================== MENU =================================
        'views/chatbot_menuitem.xml',

    ],
    'demo': [],
    'qweb': [],  # static/src/xml/*.xml
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
