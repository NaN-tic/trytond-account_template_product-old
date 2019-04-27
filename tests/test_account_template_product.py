# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
import unittest
import doctest
import trytond.tests.test_tryton
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.transaction import Transaction

from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart


class TestCase(ModuleTestCase):
    'Test module'
    module = 'account_template_product'

    def syncronize(self):
        pool = Pool()
        Syncronize = pool.get('account.chart.syncronize', type='wizard')
        Company = pool.get('company.company')
        AccountTemplate = pool.get('account.account.template')

        session_id, _, _ = Syncronize.create()
        syncronize = Syncronize(session_id)
        account_template, = AccountTemplate.search([
                ('parent', '=', None),
                ('name', '=', 'Minimal Account Chart'),
                ])
        syncronize.start.account_template = account_template
        syncronize.start.companies = Company.search([])
        syncronize.transition_syncronize()

    @with_transaction()
    def test_account_and_taxes_used(self):
        'Test account used and taxes used'
        pool = Pool()
        Currency = pool.get('currency.currency')
        Company = pool.get('company.company')
        Party = pool.get('party.party')
        Uom = pool.get('product.uom')
        User = pool.get('res.user')
        AccountTemplate = pool.get('account.account.template')
        TaxTemplate = pool.get('account.tax.template')
        TaxCodeTemplate = pool.get('account.tax.code.template')
        ProductCategory = pool.get('product.category')
        ProductTemplate = pool.get('product.template')
        TaxRuleTemplate = pool.get('account.tax.rule.template')
        TaxRuleLineTemplate = pool.get('account.tax.rule.line.template')

        account_template, = AccountTemplate.search([
                ('parent', '=', None),
                ('name', '=', 'Minimal Account Chart'),
                ])
        tax_account, = AccountTemplate.search([
                ('name', '=', 'Main Tax'),
                ])
        tax_code = TaxCodeTemplate()
        tax_code.name = 'Tax Code'
        tax_code.account = account_template
        tax_code.save()
        base_code = TaxCodeTemplate()
        base_code.name = 'Base Code'
        base_code.account = account_template
        base_code.save()
        tax = TaxTemplate()
        tax.name = tax.description = '20% VAT'
        tax.type = 'percentage'
        tax.rate = Decimal('0.2')
        tax.account = account_template
        tax.invoice_account = tax_account
        tax.credit_note_account = tax_account
        tax.invoice_base_code = base_code
        tax.invoice_base_sign = Decimal(1)
        tax.invoice_tax_code = tax_code
        tax.invoice_tax_sign = Decimal(1)
        tax.credit_note_base_code = base_code
        tax.credit_note_base_sign = Decimal(-1)
        tax.credit_note_tax_code = tax_code
        tax.credit_note_tax_sign = Decimal(-1)
        tax.save()
        new_tax, = TaxTemplate.copy([tax], {
                'name': '10% VAT',
                'description': '10% VAT',
                'rate': Decimal('0.1'),
                })
        tax_rule = TaxRuleTemplate(
            name='Test Tax Rule',
            account=account_template,
            kind='both')
        tax_rule.lines = [TaxRuleLineTemplate(
                origin_tax=tax,
                tax=new_tax,
                )]
        tax_rule.save()

        unit, = Uom.search([
                ('name', '=', 'Unit'),
                ])
        account_expense, = AccountTemplate.search([
                ('type.expense', '=', True),
                ('name', '=', 'Main Expense'),
                ])

        category = ProductCategory(name='Name')
        category.account_template_expense = account_expense
        category.customer_template_taxes = [tax]
        category.accounting = True
        category.save()
        template, = ProductTemplate.create([{
                    'name': 'test account used',
                    'default_uom': unit.id,
                    'list_price': Decimal(10),
                    'account_template_expense': account_expense,
                    'customer_template_taxes': [('add', [tax])],
                    'accounts_category': True,
                    'taxes_category': True,
                    'account_category': category,
                    }])


        # Create User Company
        admin = User.search([('login', '=', 'admin')])

        # Create Company
        company = create_company()
        user_company, = User.copy(admin)
        user_company.login = company.party.name
        user_company.main_company = company
        user_company.company = company
        user_company.save()
        company.intercompany_user = user_company
        company.save()
        with set_company(company):
            # Create Chart of Accounts
            create_chart(company)

        # Create First Branch Company
        company1 = create_company(
            name='Dunder Mifflin First Branch',
            currency=company.currency,
            )
        company1.parent = company
        user_company1, = User.copy(admin)
        user_company.login = company1.party.name
        user_company1.main_company = company1
        user_company1.company = company1
        user_company1.save()
        company1.intercompany_user = user_company1
        company1.save()

        with set_company(company1):
            # Create Chart of Accounts
            create_chart(company1)
            self.syncronize()

        Account = pool.get('account.account')
        Tax = pool.get('account.tax')
        for company in Company.search([]):
            with set_company(company):
                template = ProductTemplate(template)
                self.assertEqual(Account(template.account_expense_used).template,
                    account_expense)
                tax_used, = template.customer_taxes_used
                self.assertEqual(Tax(tax_used).template, tax)

        for company in Company.search([]):
            with set_company(company):
                template = ProductTemplate(template)
                self.assertEqual(Account(template.account_expense_used).template,
                    account_expense)
                tax_used, = template.customer_taxes_used
                self.assertEqual(Tax(tax_used).template, tax)

        # Define a tax rule on company to change it's taxes
        company1.customer_tax_rule_template = tax_rule
        company1.save()
        with set_company(company1):
            template = ProductTemplate(template)
            tax_used, = template.customer_taxes_used
            self.assertEqual(Tax(tax_used).template, new_tax)


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
