from django.db import models
from django.utils import timezone
from core.models import Company

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

class BankAccount(SoftDeleteModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bank_accounts')
    name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    agency = models.CharField(max_length=20, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.name} - {self.company.name}"

class ProductPricing(models.Model):
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

class TransactionCategory(models.Model):
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
