# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .company import *
from .product import *


def register():
    Pool.register(
        Category,
        CategoryCustomerTax,
        CategorySupplierTax,
        Template,
        TemplateCustomerTax,
        TemplateSupplierTax,
        Company,
        module='account_template_product', type_='model')
