# -*- encoding: utf-8 -*-
{
    'name': 'Website filter advanced',
    'category': 'Website/Website',
    'version': '18.0.1.0',
    'author': 'BOEK Tech',
    'description': """This module allows you to create and manage advanced filters for products in Odoo, 
                    providing an enhanced browsing experience for customers on the website or in back-office views.""",
    'summary': 'Advanced Product Filters by Category.',
    'depends': ['base', 'website_sale', 'sale_management'],
    'license': 'LGPL-3',
    'price': 100,
    'currency': 'EUR',
    'images':[
        'static/description/banner.png',
        ],
    'data': [
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/product_attribute_filter_templates.xml',
        'views/product_filter_views.xml',
        'views/product_filter_value_views.xml',
        'views/product_template_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_filter_advanced/static/src/js/custom_website_sale.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
