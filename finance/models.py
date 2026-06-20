from django.db import models
from core.models import Company, SoftDeleteModel
from core.fields import EncryptedCharField

class BankAccount(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bank_accounts')
    name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    agency = EncryptedCharField(max_length=20, blank=True, null=True)
    account_number = EncryptedCharField(max_length=50, blank=True, null=True)
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    @property
    def masked_agency(self):
        if not self.agency:
            return ""
        if len(str(self.agency)) <= 2:
            return "**"
        return "*" * (len(str(self.agency)) - 2) + str(self.agency)[-2:]

    @property
    def masked_account(self):
        if not self.account_number:
            return ""
        if len(str(self.account_number)) <= 4:
            return "****"
        return "*" * (len(str(self.account_number)) - 4) + str(self.account_number)[-4:]

    def __str__(self):
        return f"{self.name} - {self.company.name}"

class ProductPricing(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    base_cost = models.DecimalField(max_digits=12, decimal_places=2)
    gateway_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    desired_margin_percent = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    simples_nacional_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    final_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product_name

class TransactionCategory(SoftDeleteModel):
    TYPE_CHOICES = (
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transaction_categories')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    is_tax_deductible = models.BooleanField(default=False)
    
    # Simples Nacional specific mapping
    is_simples_revenue = models.BooleanField(default=False, help_text="Does this count towards Simples Nacional gross revenue (RBT12)?")

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

class Transaction(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(TransactionCategory, on_delete=models.SET_NULL, null=True, related_name='transactions')
    
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fitid = models.CharField(max_length=255, null=True, blank=True, help_text="OFX Transaction ID to prevent duplicates")
    
    # Usually a transaction is a single type, but we track it explicitly or let amount sign dictate
    # Let's enforce positive amounts and use category type to know if it's income or expense
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} - {self.description}: {self.amount}"
