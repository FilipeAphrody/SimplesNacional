from django.test import TestCase
from decimal import Decimal
from datetime import date
from core.models import Company
from finance.models import BankAccount
from .services import build_company_graph, optimize_fator_r, simulate_reforma_tributaria, analyze_sup_eligibility

class CompanyGraphTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="AI Test Co", cnpj="22.222.222/0001-22")
        self.bank = BankAccount.objects.create(company=self.company, name="Main", current_balance=Decimal('50000.00'))

    def test_graph_building_no_tx(self):
        result = build_company_graph(self.company)
        self.assertIn('account_mixing_score', result['metrics'])
        self.assertEqual(result['metrics']['runway_months'], 999.0)

class TaxEngineeringTests(TestCase):
    def test_fator_r_optimizer(self):
        # RBT12 = 100k, target payroll = 28.01% = 28010.
        # If current 11m payroll = 20000, required this month = 8010.
        rbt12 = Decimal('100000.00')
        current_payroll = Decimal('20000.00')
        required = optimize_fator_r(rbt12, current_payroll)
        self.assertEqual(required, Decimal('8010.00'))
        
        # If already hitting target
        current_payroll_safe = Decimal('30000.00')
        required_safe = optimize_fator_r(rbt12, current_payroll_safe)
        self.assertEqual(required_safe, Decimal('0.00'))
        
    def test_reforma_tributaria_simulator(self):
        # High B2B should recommend Option B
        res_b2b = simulate_reforma_tributaria(80)
        self.assertIn("Option B", res_b2b['recommendation'])
        
        # High B2C should recommend Option A
        res_b2c = simulate_reforma_tributaria(20)
        self.assertIn("Option A", res_b2c['recommendation'])
        
    def test_sup_scanner(self):
        # Professional, 2 partners (2000 each = 4000 fixed). Current tax = 10000. Savings = 6000.
        res_eligible = analyze_sup_eligibility(True, 2, Decimal('10000.00'))
        self.assertTrue(res_eligible['eligible'])
        self.assertEqual(res_eligible['savings'], Decimal('6000.00'))
        
        # Not a professional
        res_not_prof = analyze_sup_eligibility(False, 2, Decimal('10000.00'))
        self.assertFalse(res_not_prof['eligible'])
        self.assertEqual(res_not_prof['savings'], Decimal('0.00'))
