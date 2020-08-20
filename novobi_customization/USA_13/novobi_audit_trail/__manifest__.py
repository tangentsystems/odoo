{
    'name': 'Novobi: Audit Trail',
    'summary': 'Novobi: Audit Trail',
    'author': 'Novobi',
    'website': 'https://www.novobi.com/',
    'depends': [
        'base',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        
        'data/audit_trail_log_sequence.xml',
        
        'views/audit_trail_rule_views.xml',
        'views/audit_trail_log_views.xml',
    ],
    'application': False,
    'installable': True,
}
