from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from finance.models import Transaction, TransactionCategory, BankAccount
from datetime import date

@login_required
def transactions_view(request):
    company_user = request.user.companies.first()
    if not company_user:
        return redirect('dashboard')
        
    company = company_user.company
    
    if request.method == 'POST':
        # Quick and dirty transaction creation for MVP
        description = request.POST.get('description')
        amount = request.POST.get('amount')
        category_id = request.POST.get('category_id')
        
        # Get or create a default bank account for the MVP
        bank_account, _ = BankAccount.objects.get_or_create(
            company=company,
            name='Main Account'
        )
        
        category = TransactionCategory.objects.filter(id=category_id, company=company).first()
        
        if description and amount and category:
            Transaction.objects.create(
                company=company,
                bank_account=bank_account,
                category=category,
                date=date.today(),
                description=description,
                amount=amount
            )
            return redirect('transactions')

    transactions = Transaction.objects.filter(company=company).order_by('-date')
    categories = TransactionCategory.objects.filter(company=company)
    
    # If no categories exist, create some defaults
    if not categories.exists():
        TransactionCategory.objects.create(company=company, name='Service Income', type='INCOME', is_simples_revenue=True)
        TransactionCategory.objects.create(company=company, name='Software Subscriptions', type='EXPENSE')
        categories = TransactionCategory.objects.filter(company=company)

    banks = BankAccount.objects.filter(company=company)

    context = {
        'transactions': transactions,
        'categories': categories,
        'banks': banks,
    }
    return render(request, 'transactions.html', context)

@login_required
def settings_view(request):
    company_user = request.user.companies.first()
    if not company_user:
        return redirect('dashboard')
    company = company_user.company

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_bank':
            name = request.POST.get('name')
            bank_name = request.POST.get('bank_name')
            if name:
                BankAccount.objects.create(company=company, name=name, bank_name=bank_name)
                
        elif action == 'add_category':
            name = request.POST.get('name')
            type = request.POST.get('type')
            is_simples_revenue = request.POST.get('is_simples_revenue') == 'on'
            if name and type in ['INCOME', 'EXPENSE']:
                TransactionCategory.objects.create(
                    company=company, 
                    name=name, 
                    type=type, 
                    is_simples_revenue=is_simples_revenue
                )
        return redirect('settings')

    banks = BankAccount.objects.filter(company=company)
    categories = TransactionCategory.objects.filter(company=company)

    context = {
        'banks': banks,
        'categories': categories,
    }
    return render(request, 'settings.html', context)

@login_required
def import_ofx_view(request):
    from ofxparse import OfxParser
    
    company_user = request.user.companies.first()
    if not company_user:
        return redirect('dashboard')
    company = company_user.company

    if request.method == 'POST' and request.FILES.get('ofx_file'):
        ofx_file = request.FILES['ofx_file']
        bank_account_id = request.POST.get('bank_account_id')
        
        try:
            bank_account = BankAccount.objects.get(id=bank_account_id, company=company)
        except BankAccount.DoesNotExist:
            return redirect('transactions')

        # Create or get default uncategorized categories
        uncategorized_income, _ = TransactionCategory.objects.get_or_create(
            company=company, name='Uncategorized Income', type='INCOME', 
            defaults={'is_simples_revenue': False}
        )
        uncategorized_expense, _ = TransactionCategory.objects.get_or_create(
            company=company, name='Uncategorized Expense', type='EXPENSE', 
            defaults={'is_simples_revenue': False}
        )

        try:
            ofx = OfxParser.parse(ofx_file)
            for account in ofx.accounts:
                for tx in account.statement.transactions:
                    # Check if fitid already exists for this company
                    if Transaction.objects.filter(company=company, fitid=tx.id).exists():
                        continue
                        
                    amount = Decimal(str(tx.amount))
                    category = uncategorized_income if amount > 0 else uncategorized_expense
                    
                    Transaction.objects.create(
                        company=company,
                        bank_account=bank_account,
                        category=category,
                        date=tx.date.date() if hasattr(tx.date, 'date') else tx.date,
                        description=tx.memo or tx.payee or 'Imported OFX Transaction',
                        amount=abs(amount),
                        fitid=tx.id
                    )
        except Exception as e:
            # In a production environment we'd use the messages framework to show an error
            print(f"Error parsing OFX: {e}")
            
    return redirect('transactions')
