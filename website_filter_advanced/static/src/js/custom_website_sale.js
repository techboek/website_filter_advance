odoo.define('website_sale_custom.filter', function (require) {
    "use strict";

    const publicWidget = require('web.public.widget');

    publicWidget.registry.WebsiteSaleCustomFilter = publicWidget.Widget.extend({
        selector: '#wsale_products_custom_filters form, #o_wsale_offcanvas form.js_filters',
        events: {
            'change select': '_onFilterChange',
            'input input': '_onFilterChange',
        },

        _onFilterChange: function (ev) {
            this.$el.submit(); // recharge la page avec les filtres
        },
    });
});
