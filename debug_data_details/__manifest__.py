{
    "name": "Odoo debug tool",
    "version": "16.0.1.0.1",
    "summary": "Show an overview of all the fields(readonly!) on that model with the data of the current record shown under each other",
    'description': 'Show an overview of all the fields(readonly!) on that model with the data of the current record shown under each other:',
    'author': "Mainframe Monkey",
    'website': "https://www.mainframemonkey.com",
    "depends": ["web"],
    "category": "Tools",
    "data": [
    ],
    "assets": {
        'web.assets_backend': [
            'debug_data_details/static/src/xml/action_dialog.xml',
            'debug_data_details/static/src/js/debug_items.js',
        ],
    },
    "installable": True,
    "application": True,
    "license": 'LGPL-3',
}
