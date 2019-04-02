# The COPYRIGHT file at the top level of this repository contains the fulli
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Company']


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'
    customer_tax_rule_template = fields.Many2One('account.tax.rule.template',
        'Customer Tax Rule',
        help=('If defined it will be applied on the the customer template '
            'taxes defined on product template for this company'))
    supplier_tax_rule_template = fields.Many2One('account.tax.rule.template',
        'Supplier Tax Rule',
        help=('If defined it will be applied on the the supplier template '
            'taxes defined on product template for this company'))
