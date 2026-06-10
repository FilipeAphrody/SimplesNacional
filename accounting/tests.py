from django.test import TestCase
from decimal import Decimal
from datetime import date
from core.models import Company
from accounting.models import RevenueRecord
from .services import calculate_fator_r

class SimplesNacionalTaxTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company", cnpj="11.111.111/0001-11")

    def test_fator_r_calculation_safe(self):
        # rbt12 = 100k, payroll = 30k -> 30% -> >= 28% -> safe (Anexo III)
        # Create records for the last 10 months (10k revenue, 3k payroll per month)
        for i in range(1, 11):
            RevenueRecord.objects.create(
                company=self.company,
                month=i,
                year=2023,
                gross_revenue=Decimal('10000.00'),
                payroll_expense=Decimal('3000.00')
            )
        fator_r = calculate_fator_r(self.company, 11, 2023)
        self.assertEqual(fator_r, Decimal('0.30'))
        self.assertTrue(fator_r >= Decimal('0.28'))

    def test_fator_r_calculation_danger(self):
        # rbt12 = 100k, payroll = 20k -> 20% -> < 28% -> danger (Anexo V)
        for i in range(1, 11):
            RevenueRecord.objects.create(
                company=self.company,
                month=i,
                year=2023,
                gross_revenue=Decimal('10000.00'),
                payroll_expense=Decimal('2000.00')
            )
        fator_r = calculate_fator_r(self.company, 11, 2023)
        self.assertEqual(fator_r, Decimal('0.20'))
        self.assertFalse(fator_r >= Decimal('0.28'))
