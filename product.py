# The COPYRIGHT file at the top level of this repository contains the fulli
# copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta

__all__ = ['Category', 'CategoryCustomerTax', 'CategorySupplierTax',
    'Template', 'TemplateCustomerTax', 'TemplateSupplierTax']
__metaclass__ = PoolMeta


class Category:
    __name__ = 'product.category'
    account_template_expense = fields.Many2One('account.account.template',
        'Account Template Expense',
        domain=[
            ('kind', '=', 'expense'),
            ],
        states={
            'invisible': Eval('account_parent', False),
            },
        depends=['account_parent'])
    account_template_revenue = fields.Many2One('account.account.template',
        'Account Template Revenue',
        domain=[
            ('kind', '=', 'revenue'),
            ],
        states={
            'invisible': Eval('account_parent', False),
            },
        depends=['account_parent'])
    customer_template_taxes = fields.Many2Many(
        'product.category-customer-account.tax.template',
        'product', 'tax', 'Customer Template Taxes',
        domain=[
            ('parent', '=', None),
            ['OR',
                ('group', '=', None),
                ('group.kind', 'in', ['sale', 'both'])],
            ],
        states={
            'invisible': Eval('taxes_parent', False),
            },
        depends=['taxes_parent'])
    supplier_template_taxes = fields.Many2Many(
        'product.category-supplier-account.tax.template',
        'product', 'tax',
        'Supplier Template Taxes',
        domain=[
            ('parent', '=', None),
            ['OR',
                ('group', '=', None),
                ('group.kind', 'in', ['purchase', 'both'])],
            ],
        states={
            'invisible': Eval('taxes_parent', False),
            },
        depends=['taxes_parent'])

    @classmethod
    def __setup__(cls):
        super(Category, cls).__setup__()
        for source_name, target_name in [
                (('account_expense'), ('account_template_expense')),
                (('account_revenue'), ('account_template_revenue')),
                (('customer_taxes'), ('customer_template_taxes')),
                (('supplier_taxes'), ('supplier_template_taxes')),
                ]:
            field = getattr(cls, source_name)
            if target_name not in field.depends:
                old_invisible = field.states.get('invisible')
                invisible = Bool(Eval(target_name))
                if old_invisible:
                    invisible |= old_invisible
                field.states['invisible'] = invisible
                field.depends.append(target_name)

    def get_account(self, name):
        pool = Pool()
        Company = pool.get('company.company')
        account = super(Category, self).get_account(name)
        template_name = 'account_template_%s' % name[:-5].split('_')[-1]
        if not self.account_parent and hasattr(self, template_name):
            template = getattr(self, template_name)
            company = Transaction().context.get('company')
            if template and company:
                account = template.get_syncronized_company_value(
                    Company(company)).id
        return account

    def get_taxes(self, name):
        pool = Pool()
        Company = pool.get('company.company')
        taxes = super(Category, self).get_taxes(name)
        tax_type = name.split('_')[0]
        template_name = '%s_template_taxes' % tax_type
        if not self.taxes_parent and hasattr(self, template_name):
            tax_templates = getattr(self, template_name)
            company = Transaction().context.get('company')
            if tax_templates and company:
                taxes = []
                company = Company(company)
                tax_rule = None
                tax_rule_template = getattr(company,
                    '%s_tax_rule_template' % tax_type)
                # Apply tax_rule in templates
                if tax_rule_template:
                    tax_rule = tax_rule_template.get_syncronized_company_value(
                        company)
                for template in tax_templates:
                    tax = template.get_syncronized_company_value(company)
                    if tax:
                        if tax_rule:
                            taxes.extend(tax_rule.apply(tax, {}))
                        else:
                            taxes.append(tax.id)
        return taxes

    @fields.depends('account_parent', 'account_category_expense')
    def on_change_account_parent_expense(self):
        result = {}
        if not self.account_parent:
            supplier_taxes = []
            if self.account_parent_expense:
                supplier_taxes.extend(
                    tax.id for tax in self.account_parent_expense.taxes)
            result = {
                'supplier_category_taxes': supplier_taxes,
            }
        return result

    @fields.depends('account_parent', 'account_template_revenue')
    def on_change_account_revenue(self):
        result = {}
        if not self.account_parent:
            customer_taxes = []
            if self.account_template_revenue:
                customer_taxes.extend(
                    tax.id for tax in self.account_template_revenue.taxes)
            result = {
                'customer_template_taxes': customer_taxes,
            }
        return result


class CategoryCustomerTax(ModelSQL):
    'Product Category - Customer category Tax'
    __name__ = 'product.category-customer-account.tax.template'
    _table = 'product_category_customer_taxes_template_rel'
    product = fields.Many2One('product.category', 'Product Category',
        ondelete='CASCADE', select=True, required=True)
    tax = fields.Many2One('account.tax.template', 'Tax Template',
        required=True, select=True)


class CategorySupplierTax(ModelSQL):
    'Product Category - Supplier category Tax'
    __name__ = 'product.category-supplier-account.tax.template'
    _table = 'product_category_supplier_taxes_template_rel'
    product = fields.Many2One('product.category', 'Product Category',
            ondelete='CASCADE', select=True, required=True)
    tax = fields.Many2One('account.tax.template', 'Tax Template',
            required=True, select=True)


class Template:
    __name__ = 'product.template'
    account_template_expense = fields.Many2One('account.account.template',
        'Account Template Expense',
        domain=[
            ('kind', '=', 'expense'),
            ],
        states={
            'invisible': Eval('account_category', False),
            },
        depends=['account_category'])
    account_template_revenue = fields.Many2One('account.account.template',
        'Account Template Revenue',
        domain=[
            ('kind', '=', 'revenue'),
            ],
        states={
            'invisible': Eval('account_category', False),
            },
        depends=['account_category'])
    customer_template_taxes = fields.Many2Many(
        'product.template-customer-account.tax.template',
        'product', 'tax', 'Customer Template Taxes',
        domain=[
            ('parent', '=', None),
            ['OR',
                ('group', '=', None),
                ('group.kind', 'in', ['sale', 'both'])],
            ],
        states={
            'invisible': Eval('taxes_category', False),
            },
        depends=['taxes_category'])
    supplier_template_taxes = fields.Many2Many(
        'product.template-supplier-account.tax.template',
        'product', 'tax',
        'Supplier Template Taxes',
        domain=[
            ('parent', '=', None),
            ['OR',
                ('group', '=', None),
                ('group.kind', 'in', ['purchase', 'both'])],
            ],
        states={
            'invisible': Eval('taxes_category', False),
            },
        depends=['taxes_category'])

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()
        for source_name, target_name in [
                (('account_expense'), ('account_template_expense')),
                (('account_revenue'), ('account_template_revenue')),
                (('customer_taxes'), ('customer_template_taxes')),
                (('supplier_taxes'), ('supplier_template_taxes')),
                ]:
            field = getattr(cls, source_name)
            if target_name not in field.depends:
                old_invisible = field.states.get('invisible')
                invisible = Bool(Eval(target_name))
                if old_invisible:
                    invisible |= old_invisible
                field.states['invisible'] = invisible
                required = field.states.get('required')
                if required:
                    field.states['required'] = (~Bool(Eval(target_name))
                        & required)
                    # Copy required from source field
                    target_field = getattr(cls, target_name)
                    target_field.states['required'] = (~Bool(Eval(source_name))
                        & required)
                    target_field.depends = list(set(field.depends) |
                        set(target_field.depends))
                field.depends.append(target_name)

    def get_account(self, name):
        pool = Pool()
        Company = pool.get('company.company')
        account = super(Template, self).get_account(name)
        template_name = 'account_template_%s' % name[:-5].split('_')[-1]
        if not self.account_category and hasattr(self, template_name):
            template = getattr(self, template_name)
            company = Transaction().context.get('company')
            if template and company:
                account = template.get_syncronized_company_value(
                    Company(company)).id
        return account

    def get_taxes(self, name):
        pool = Pool()
        Company = pool.get('company.company')
        taxes = super(Template, self).get_taxes(name)
        tax_type = name.split('_')[0]
        template_name = '%s_template_taxes' % tax_type
        if not self.taxes_category and hasattr(self, template_name):
            tax_templates = getattr(self, template_name)
            company = Transaction().context.get('company')
            if tax_templates and company:
                taxes = []
                company = Company(company)
                tax_rule = None
                tax_rule_template = getattr(company,
                    '%s_tax_rule_template' % tax_type)
                # Apply tax_rule in templates
                if tax_rule_template:
                    tax_rule = tax_rule_template.get_syncronized_company_value(
                        company)
                for template in tax_templates:
                    tax = template.get_syncronized_company_value(company)
                    if tax:
                        if tax_rule:
                            taxes.extend(tax_rule.apply(tax, {}))
                        else:
                            taxes.append(tax.id)
        return taxes

    @fields.depends('account_category', 'account_template_expense')
    def on_change_account_template_expense(self):
        result = {}
        if not self.account_category:
            supplier_taxes = []
            if self.account_template_expense:
                supplier_taxes.extend(
                    tax.id for tax in self.account_template_expense.taxes)
            result = {
                'supplier_template_taxes': supplier_taxes,
            }
        return result

    @fields.depends('account_category', 'account_template_revenue')
    def on_change_account_revenue(self):
        result = {}
        if not self.account_category:
            customer_taxes = []
            if self.account_template_revenue:
                customer_taxes.extend(
                    tax.id for tax in self.account_template_revenue.taxes)
            result = {
                'customer_tempmlate_taxes': customer_taxes,
            }
        return result


class TemplateCustomerTax(ModelSQL):
    'Product Template - Customer Template Tax'
    __name__ = 'product.template-customer-account.tax.template'
    _table = 'product_customer_taxes_template_rel'
    product = fields.Many2One('product.template', 'Product Template',
        ondelete='CASCADE', select=True, required=True)
    tax = fields.Many2One('account.tax.template', 'Tax Template',
        required=True, select=True)


class TemplateSupplierTax(ModelSQL):
    'Product Template - Supplier Template Tax'
    __name__ = 'product.template-supplier-account.tax.template'
    _table = 'product_supplier_taxes_template_rel'
    product = fields.Many2One('product.template', 'Product Template',
            ondelete='CASCADE', select=True, required=True)
    tax = fields.Many2One('account.tax.template', 'Tax Template',
            required=True, select=True)
