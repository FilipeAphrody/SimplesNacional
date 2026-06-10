from django.test import TestCase
from decimal import Decimal
from core.models import Company
from .models import ProductPricing

class PricingCalculatorTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Pricing Test Co", cnpj="33.333.333/0001-33")

    def test_pricing_formula(self):
        # Formula: Price = Cost / (1 - (Tax% + Fee% + Margin%))
        # Cost = 100, Tax = 6%, Fee = 5%, Margin = 20%
        # Total Deductions = 31% = 0.31
        # Divisor = 1 - 0.31 = 0.69
        # Price = 100 / 0.69 = 144.9275...
        
        base_cost = Decimal('100.00')
        tax = Decimal('6.00')
        fee = Decimal('5.00')
        margin = Decimal('20.00')
        
        total_deductions_percent = (tax + fee + margin) / Decimal('100')
        final_price = base_cost / (Decimal('1') - total_deductions_percent)
        
        self.assertAlmostEqual(final_price, Decimal('144.93'), places=2)
        
        # Verify creating the record works
        pricing = ProductPricing.objects.create(
            company=self.company,
            product_name="Test Service",
            base_cost=base_cost,
            gateway_fee_percent=fee,
            desired_margin_percent=margin,
            simples_nacional_rate=tax,
            final_price=final_price
        )
        self.assertEqual(pricing.product_name, "Test Service")

from datetime import date
from .models import Transaction, BankAccount, TransactionCategory

class SoftDeletionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Soft Delete Co", cnpj="44.444.444/0001-44")
        self.bank = BankAccount.objects.create(company=self.company, name="Test Bank")
        self.category = TransactionCategory.objects.create(company=self.company, name="Sales", type="INCOME")
        self.tx = Transaction.objects.create(
            company=self.company,
            bank_account=self.bank,
            category=self.category,
            date=date.today(),
            description="Test Sale",
            amount=Decimal('1000.00')
        )

    def test_soft_delete_transaction(self):
        self.assertEqual(Transaction.objects.count(), 1)
        self.tx.delete()
        
        # It should disappear from default manager
        self.assertEqual(Transaction.objects.count(), 0)
        
        # But still exist in all_objects manager and have is_deleted=True
        self.assertEqual(Transaction.all_objects.count(), 1)
        deleted_tx = Transaction.all_objects.first()
        self.assertTrue(deleted_tx.is_deleted)
        self.assertIsNotNone(deleted_tx.deleted_at)
        
    def test_restore_transaction(self):
        self.tx.delete()
        self.assertEqual(Transaction.objects.count(), 0)
        
        # Restore it
        deleted_tx = Transaction.all_objects.first()
        deleted_tx.restore()
        
        # It should reappear
        self.assertEqual(Transaction.objects.count(), 1)
        restored_tx = Transaction.objects.first()
        self.assertFalse(restored_tx.is_deleted)
        self.assertIsNone(restored_tx.deleted_at)
