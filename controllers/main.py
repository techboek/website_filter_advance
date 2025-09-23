# -*- coding: utf-8 -*-

import logging
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.main import TableCompute
import logging
from datetime import datetime
from werkzeug.exceptions import Forbidden, NotFound

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.tools import lazy

_logger = logging.getLogger(__name__)


class WebsiteSaleCustom(WebsiteSale):

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=WebsiteSale.sitemap_shop)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        add_qty = int(post.get('add_qty', 1))
        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0

        Category = request.env['product.public.category']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        website = request.env['website'].get_current_website()
        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = website.shop_ppg or 20

        ppr = website.shop_ppr or 4

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values} if attrib_values else set()
        attrib_set = {v[1] for v in attrib_values} if attrib_values else set()

        # --- VOTRE LOGIQUE : Récupérer les filtres personnalisés ---
        filter_list = request.httprequest.args.getlist('filter')
        filter_values = [[int(x) for x in v.split("-")] for v in filter_list if v]
        filter_ids = {v[0] for v in filter_values}
        filter_value_set = {v[1] for v in filter_values}

        keep = QueryURL('/shop',
                        **self._shop_get_query_url_kwargs(category and int(category), search, min_price, max_price,
                                                          **post))

        now = datetime.timestamp(datetime.now())
        pricelist = request.env['product.pricelist'].browse(request.session.get('website_sale_current_pl'))
        if not pricelist or request.session.get('website_sale_pricelist_time',
                                                0) < now - 60 * 60:  # test: 1 hour in session
            pricelist = website.get_current_pricelist()
            request.session['website_sale_pricelist_time'] = now
            request.session['website_sale_current_pl'] = pricelist.id

        request.update_context(pricelist=pricelist.id, partner=request.env.user.partner_id)

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            company_currency = website.company_id.currency_id
            conversion_rate = request.env['res.currency']._get_conversion_rate(
                company_currency, pricelist.currency_id, request.website.company_id, fields.Date.today())
        else:
            conversion_rate = 1

        url = "/shop"
        if search:
            post["search"] = search
        if attrib_list:
            post['attrib'] = attrib_list
        if filter_list:
            post['filter'] = filter_list

        options = self._get_search_options(
            category=category,
            attrib_values=attrib_values,
            pricelist=pricelist,
            min_price=min_price,
            max_price=max_price,
            conversion_rate=conversion_rate,
            **post
        )
        fuzzy_search_term, product_count, search_product = self._shop_lookup_products(attrib_set, options, post, search,
                                                                                      website)

        # --- VOTRE LOGIQUE : Appliquer les filtres personnalisés ---
        if filter_values:
            # Pour CHAQUE filtre sélectionné, trouver les produits correspondants
            product_ids_by_filter = []

            for filter_id, value_id in filter_values:
                # Trouver les produits pour ce filtre spécifique
                product_ids = request.env['product.filter.line'].sudo().search([
                    ('filter_id', '=', filter_id),
                    ('value_ids', '=', value_id)
                ]).mapped('product_id')
                product_ids_by_filter.append(set(product_ids.ids))

            # Intersection de tous les ensembles de produits
            if product_ids_by_filter:
                common_product_ids = set.intersection(*product_ids_by_filter)
                # Filtrer les produits de recherche
                search_product = search_product.filtered(lambda p: p.id in common_product_ids)
                product_count = len(search_product)
            else:
                # Aucun produit ne correspond à tous les filtres
                search_product = request.env['product.template']
                product_count = 0

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            # TODO Find an alternative way to obtain the domain through the search metadata.
            Product = request.env['product.template'].with_context(bin_size=True)
            domain = self._get_search_domain(search, category, attrib_values)

            # This is ~4 times more efficient than a search for the cheapest and most expensive products
            query = Product._where_calc(domain)
            Product._apply_ir_rules(query, 'read')
            from_clause, where_clause, where_params = query.get_sql()
            query = f"""
                SELECT COALESCE(MIN(list_price), 0) * {conversion_rate}, COALESCE(MAX(list_price), 0) * {conversion_rate}
                  FROM {from_clause}
                 WHERE {where_clause}
            """
            request.env.cr.execute(query, where_params)
            available_min_price, available_max_price = request.env.cr.fetchone()

            if min_price or max_price:
                # The if/else condition in the min_price / max_price value assignment
                # tackles the case where we switch to a list of products with different
                # available min / max prices than the ones set in the previous page.
                # In order to have logical results and not yield empty product lists, the
                # price filter is set to their respective available prices when the specified
                # min exceeds the max, and / or the specified max is lower than the available min.
                if min_price:
                    min_price = min_price if min_price <= available_max_price else available_min_price
                    post['min_price'] = min_price
                if max_price:
                    max_price = max_price if max_price >= available_min_price else available_max_price
                    post['max_price'] = max_price

        website_domain = website.website_domain()
        categs_domain = [('parent_id', '=', False)] + website_domain
        if search:
            search_categories = Category.search(
                [('product_tmpl_ids', 'in', search_product.ids)] + website_domain
            ).parents_and_self
            categs_domain.append(('id', 'in', search_categories.ids))
        else:
            search_categories = Category
        categs = lazy(lambda: Category.search(categs_domain))

        if category:
            url = "/shop/category/%s" % slug(category)

        pager = website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        offset = pager['offset']
        products = search_product[offset:offset + ppg]

        ProductAttribute = request.env['product.attribute']
        if products:
            # get all products without limit
            attributes = lazy(lambda: ProductAttribute.search([
                ('product_tmpl_ids', 'in', search_product.ids),
                ('visibility', '=', 'visible'),
            ]))
        else:
            attributes = lazy(lambda: ProductAttribute.browse(attributes_ids))

        # --- VOTRE LOGIQUE : Calculer les filtres personnalisés disponibles ---
        custom_filters = {}
        if search_product:
            # Récupérer tous les IDs de filtres liés aux produits
            product_filter_lines = request.env['product.filter.line'].sudo().search([
                ('product_id', 'in', search_product.ids)
            ])

            filter_ids = list(set(product_filter_lines.mapped('filter_id').ids))
            value_ids = list(set(product_filter_lines.mapped('value_ids').ids))

            # Récupérer les filtres et leurs valeurs
            filters = request.env['product.filter'].sudo().browse(filter_ids)

            for f in filters:
                # Récupérer les valeurs de ce filtre qui sont utilisées
                used_values = request.env['product.filter.value'].sudo().search([
                    ('id', 'in', value_ids),
                    ('filter_id', '=', f.id)
                ], order='sequence, name')

                if used_values:
                    custom_filters[f] = used_values

        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            if website.viewref('website_sale.products_list_view').active:
                layout_mode = 'list'
            else:
                layout_mode = 'grid'
            request.session['website_sale_shop_layout_mode'] = layout_mode

        products_prices = lazy(lambda: products._get_sales_prices(pricelist))

        fiscal_position_id = website._get_current_fiscal_position_id(request.env.user.partner_id)

        values = {
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'order': post.get('order', ''),
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'add_qty': add_qty,
            'products': products,
            'search_product': search_product,
            'search_count': product_count,  # common for all searchbox
            'bins': lazy(lambda: TableCompute().process(products, ppg, ppr)),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
            'products_prices': products_prices,
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
            'float_round': tools.float_round,
            'fiscal_position_id': fiscal_position_id,
            # --- VOS VALEURS AJOUTÉES ---
            'custom_filters': custom_filters,
            'filter_values': filter_list,
        }
        if filter_by_price_enabled:
            values['min_price'] = min_price or available_min_price
            values['max_price'] = max_price or available_max_price
            values['available_min_price'] = tools.float_round(available_min_price, 2)
            values['available_max_price'] = tools.float_round(available_max_price, 2)
        if category:
            values['main_object'] = category
        values.update(self._get_additional_shop_values(values))

        # Debug logging
        _logger.info(f"Custom filters: {len(custom_filters)}")
        _logger.info(f"Active filters: {filter_values}")
        _logger.info(f"Products after filtering: {product_count}")

        return request.render("website_sale.products", values)



# # -*- coding: utf-8 -*-
#
# import logging
# from odoo import http
# from odoo.http import request
# from odoo.addons.website_sale.controllers.main import WebsiteSale
# from odoo.addons.website_sale.controllers.main import TableCompute
# from odoo.tools import lazy
# _logger = logging.getLogger(__name__)
#
#
# class WebsiteSaleCustom(WebsiteSale):
#
#     @http.route([
#         '/shop',
#         '/shop/page/<int:page>',
#         '/shop/category/<model("product.public.category"):category>',
#         '/shop/category/<model("product.public.category"):category>/page/<int:page>',
#     ], type='http', auth="public", website=True)
#     def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
#         # --- appel de la logique originale ---
#         response = super().shop(page=page, category=category, search=search,
#                                 min_price=min_price, max_price=max_price, ppg=ppg, **post)
#
#         # --- récupération du context rendu par le super() ---
#         values = response.qcontext
#
#         # --- lecture des filtres personnalisés depuis l'URL ---
#         filter_list = request.httprequest.args.getlist('filter')
#         filter_values = [[int(x) for x in v.split("-")] for v in filter_list if v]
#         filter_ids = {v[0] for v in filter_values}
#         filter_value_set = {v[1] for v in filter_values}
#         _logger.info(f"Liste des filtres {list(filter_value_set)}")
#         # --- filtrage des produits déjà calculés par le super() ---
#         if filter_values:
#             product_ids = request.env['product.filter.line'].sudo().search([
#                 ('filter_id', 'in', list(filter_ids)),
#                 ('value_ids', 'in', list(filter_value_set))
#             ]).mapped('product_id')
#             values['products'] = values['products'].filtered(lambda p: p in product_ids)
#             values['search_count'] = len(values['products'])
#             print('Produit filtrer : ', values['products'])
#
#             # 🔥 recalcul de bins pour que le template affiche bien la grille mise à jour
#             ppg = values.get('ppg') or 20  # sécurité si ppg n’existe pas
#             website = request.env['website'].get_current_website()
#             ppr = website.shop_ppr or 4
#             values['bins'] = lazy(lambda: TableCompute().process(values['products'], ppg, ppr))
#
#         # Récupérer tous les filtres liés aux produits listés
#         custom_filters = request.env['product.filter'].sudo().search([
#             ('id', 'in', values['products'].mapped('filter_line_ids.filter_id').ids)
#         ])
#
#         # Pour chaque filtre, limiter ses valeurs aux produits affichés
#         filter_with_values = {}
#         for f in custom_filters:
#             # Récupérer uniquement les valeurs utilisées par les produits affichés
#             used_values = request.env['product.filter.value'].sudo().search([
#                 ('id', 'in', values['products'].mapped('filter_line_ids.value_ids').ids),
#                 ('filter_id', '=', f.id)
#             ])
#             filter_with_values[f] = used_values
#             print('valeur des filtre', f)
#
#         pager = request.website.pager(
#             url="/shop",
#             total=values['search_count'],
#             page=page,
#             step=ppg or 20,
#             url_args=post,
#         )
#         values['pager'] = pager
#
#         # --- passage des filtres au template ---
#         values['custom_filters'] = filter_with_values
#         values['filter_values'] = filter_list
#
#         return request.render("website_sale.products", values)
