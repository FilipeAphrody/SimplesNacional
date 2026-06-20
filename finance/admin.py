from django.contrib import admin
from .models import BankAccount, TransactionCategory, Transaction

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'initial_balance', 'is_deleted')
    list_filter = ('company', 'is_deleted')
    search_fields = ('name', 'company__name')

@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'company', 'is_simples_revenue')
    list_filter = ('type', 'company', 'is_simples_revenue')
    search_fields = ('name',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'date', 'category', 'bank_account', 'company', 'is_deleted')
    list_filter = ('company', 'category__type', 'is_deleted')
    search_fields = ('description', 'company__name')
    date_hierarchy = 'date'
