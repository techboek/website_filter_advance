/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import '@website_sale/js/website_sale'


publicWidget.registry.WebsiteSaleCustomFilter = publicWidget.Widget.extend({
    selector: 'form.js_filters, #o_wsale_offcanvas form.js_filters',
    events: {
        'change select': '_onFilterChange',
        'input input': '_onFilterChange',
    },

    _onFilterChange: function (ev) {
        this.$el.submit(); // recharge la page avec les filtres
    },
});
