# -*- coding: utf-8 -*-
from random import randint
from odoo.exceptions import ValidationError
from odoo import models, fields, api

class ProductFilter(models.Model):
    _name = "product.filter"
    _description = "Product Filter"

    name = fields.Char(string="Filter name", required=True)
    type = fields.Selection([
        ('radio', 'Radio'),
        ('color', 'Color')], default='radio', required=True)
    value_ids = fields.One2many("product.filter.value", "filter_id", string="Possible values")
    company_id = fields.Many2one('res.company', string='Company')


class ProductFilterValue(models.Model):
    _name = "product.filter.value"
    _description = "Product Filter Value"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string="Value", required=True)
    filter_id = fields.Many2one("product.filter", string="Filter", required=True, ondelete="cascade")
    sequence = fields.Integer(string="Sequence", default=10)
    html_color = fields.Char(
        string='Color',
        help="Here you can set a specific HTML color index (e.g. #ff0000) to display the color if the attribute type is 'Color'.")
    color = fields.Integer('Color Index', default=_get_default_color)


class ProductFilterLine(models.Model):
    _name = "product.filter.line"
    _description = "Product Filter Line"

    product_id = fields.Many2one("product.template", string="Product", required=True, ondelete="cascade")
    filter_id = fields.Many2one("product.filter", string="Filter", required=True)
    value_ids = fields.Many2many(
        "product.filter.value",
        string="Values",
        domain="[('filter_id', '=', filter_id)]",
        required=True
    )

    @api.onchange("filter_id")
    def _onchange_filter_id(self):
        if self.filter_id:
            return {
                "domain": {
                    "value_ids": [("filter_id", "=", self.filter_id.id)]
                }
            }
        return {"domain": {"value_ids": []}}

    @api.constrains("product_id", "filter_id", "value_ids")
    def _check_unique_filter(self):
        for line in self:
            others = self.search([
                ("id", "!=", line.id),
                ("product_id", "=", line.product_id.id),
                ("filter_id", "=", line.filter_id.id),
            ])
            if others:
                raise ValidationError(
                    f"Product '{line.product_id.name}' is already filtered '{line.filter_id.name}'."
                )




