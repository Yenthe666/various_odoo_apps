# -*- coding: utf-8 -*-
{
    'name': "Audit Log extra",

    'summary': """
        Extend functionalities of Audit Log
    """,

    'description': """
        Extend functionalities of Audit Log
    """,

    'author': "Mainframe Monkey",
    'website': "http://www.mainframemonkey.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '14.0.0.1',

    'depends': ['auditlog'],

    # always loaded
    'data': [
        'views/auditlog_rule_views.xml',
        'views/auditlog_log_views.xml',
    ],

    'uninstall_hook': 'uninstall_hook',
}
