# -*- coding: utf-8 -*-

from email.policy import default
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    filter_line_ids = fields.One2many("product.filter.line", "product_id", string="Filters")
