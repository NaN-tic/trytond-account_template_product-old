# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
import unittest
import doctest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class TestCase(unittest.TestCase):
    'Test module'

    def setUp(self):
        trytond.tests.test_tryton.install_module('account_template_product')

    def test0005views(self):
        'Test views'
        test_view('account_template_product')

    def test0006depends(self):
        'Test depends'
        test_depends()

    def create_chart(self, company):
        User = POOL.get('res.user')
        Account = POOL.get('account.account')
        Template = POOL.get('account.account.template')
        CreateChart = POOL.get('account.create_chart', type='wizard')
        user = User(USER)
        previous_company = user.company
        previous_main_company = user.main_company
        User.write([user], {
                'main_company': company.id,
                'company': company.id,
                })
        CONTEXT.update(User.get_preferences(context_only=True))
        account_template, = Template.search([
                ('parent', '=', None),
                ])
        session_id, _, _ = CreateChart.create()
        create_chart = CreateChart(session_id)
        create_chart.account.account_template = account_template
        create_chart.account.company = company
        create_chart.transition_create_account()
        receivable, = Account.search([
                ('kind', '=', 'receivable'),
                ('company', '=', company.id),
                ], limit=1)
        payable, = Account.search([
                ('kind', '=', 'payable'),
                ('company', '=', company.id),
                ], limit=1)
        create_chart.properties.company = company
        create_chart.properties.account_receivable = receivable
        create_chart.properties.account_payable = payable
        create_chart.transition_create_properties()
        User.write([user], {
                'main_company': (previous_main_company.id
                    if previous_main_company else None),
                'company': previous_company.id if previous_company else None,
                })
        CONTEXT.update(User.get_preferences(context_only=True))

    def syncronize(self):
        Syncronize = POOL.get('account.chart.syncronize', type='wizard')
        Company = POOL.get('company.company')
        AccountTemplate = POOL.get('account.account.template')

        session_id, _, _ = Syncronize.create()
        syncronize = Syncronize(session_id)
        account_template, = AccountTemplate.search([
                ('parent', '=', None),
                ])
        syncronize.start.account_template = account_template
        syncronize.start.companies = Company.search([])
        syncronize.transition_syncronize()

    def test_account_and_taxes_used(self):
        'Test account used and taxes used'
        Currency = POOL.get('currency.currency')
        Company = POOL.get('company.company')
        Party = POOL.get('party.party')
        Uom = POOL.get('product.uom')
        AccountTemplate = POOL.get('account.account.template')
        TaxTemplate = POOL.get('account.tax.template')
        TaxCodeTemplate = POOL.get('account.tax.code.template')
        ProductCategory = POOL.get('product.category')
        ProductTemplate = POOL.get('product.template')
        TaxRuleTemplate = POOL.get('account.tax.rule.template')
        TaxRuleLineTemplate = POOL.get('account.tax.rule.line.template')

        with Transaction().start(DB_NAME, USER, context=CONTEXT) as trans:
            account_template, = AccountTemplate.search([
                    ('parent', '=', None),
                    ])
            tax_account, = AccountTemplate.search([
                    ('name', '=', 'Main Tax'),
                    ])
            with trans.set_user(0):
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

            main_company, = Company.search([
                    ('rec_name', '=', 'Dunder Mifflin'),
                    ], limit=1)
            currency1, = Currency.search([
                    ('code', '=', 'cu1'),
                    ], 0, 1, None)

            party1, = Party.create([{
                        'name': 'Dunder Mifflin First Branch',
                        }])
            company1, = Company.create([{
                        'party': party1.id,
                        'parent': main_company.id,
                        'currency': currency1.id,
                        }])
            self.create_chart(company1)
            self.syncronize()
            unit, = Uom.search([
                    ('name', '=', 'Unit'),
                    ])
            unit_id = unit.id
            account_expense, = AccountTemplate.search([
                    ('kind', '=', 'expense'),
                    ])

            category = ProductCategory(name='Name')
            category.account_template_expense = account_expense
            category.customer_template_taxes = [tax]
            category.save()

            template = ProductTemplate(
                name='test account used',
                list_price=Decimal(10),
                cost_price=Decimal(3),
                default_uom=unit_id,
                account_template_expense=account_expense,
                customer_template_taxes=[tax],
                )
            template.save()

            for company in Company.search([]):
                with Transaction().set_context(company=company.id):
                    template = ProductTemplate(template)
                    self.assertEqual(template.account_expense_used.template,
                        account_expense)
                    tax_used, = template.customer_taxes_used
                    self.assertEqual(tax_used.template, tax)

            template.account_category = True
            template.taxes_category = True
            template.category = category
            template.save()

            for company in Company.search([]):
                with Transaction().set_context(company=company.id):
                    template = ProductTemplate(template)
                    self.assertEqual(template.account_expense_used.template,
                        account_expense)
                    tax_used, = template.customer_taxes_used
                    self.assertEqual(tax_used.template, tax)

            # Define a tax rule on company to change it's taxes
            company1.customer_tax_rule_template = tax_rule
            company1.save()
            with Transaction().set_context(company=company1.id):
                template = ProductTemplate(template)
                tax_used, = template.customer_taxes_used
                self.assertEqual(tax_used.template, new_tax)


def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.account.tests import test_account
    for test in test_account.suite():
        if test not in suite and not isinstance(test, doctest.DocTestCase):
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
