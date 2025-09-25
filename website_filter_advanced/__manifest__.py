# -*- encoding: utf-8 -*-
{
    'name': 'Website filter advanced',
    'category': 'Website/Website',
    'version': '16.0.1.0',
    'author': 'BOEK Tech',
    'description': """Ce module permet de créer et gérer des filtres avancés pour les produits dans Odoo, 
        offrant une expérience de navigation améliorée pour les clients sur le site web ou dans les vues back-office.""",
    'summary': 'Advanced Product Filters by Category.',
    'depends': ['website_sale', 'sale_management'],
    'license': 'LGPL-3',
    'price': 100,
    'currency': 'EUR',
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
