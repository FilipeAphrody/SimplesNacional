from django.test import TestCase
from core.models import Company
from finance.models import BankAccount
from .services import build_company_graph

class AICFOTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="AI Test Company", cnpj="22.222.222/0001-22")
        self.bank = BankAccount.objects.create(company=self.company, name="Nubank", current_balance=5000.00)

    def test_graph_and_runway_calculation(self):
        graph_data = build_company_graph(self.company)
        metrics = graph_data['metrics']
        
        # With no transactions, runway should be 999 (infinite) and balance 5000
        self.assertEqual(metrics['total_cash'], 5000.00)
        self.assertEqual(metrics['avg_burn'], 0.0)
        self.assertEqual(metrics['runway_months'], 999.0)
