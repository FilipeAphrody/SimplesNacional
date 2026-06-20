from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from finance.models import Transaction, TransactionCategory, BankAccount, ProductPricing
from core.models import Company
from datetime import date, datetime
from decimal import Decimal
from accounting.services import calculate_monthly_das

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
        
        category = TransactionCategory.objects.filter(id=category_id, company=company).first() if category_id else None
        
        if description and amount:
            if not category:
                from ai.services import auto_categorize_transaction
                category = auto_categorize_transaction(description, company)
                
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
            agency = request.POST.get('agency')
            account_number = request.POST.get('account_number')
            if name:
                BankAccount.objects.create(
                    company=company, 
                    name=name, 
                    bank_name=bank_name,
                    agency=agency,
                    account_number=account_number
                )
                
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

        from ai.services import auto_categorize_transaction
        
        try:
            ofx = OfxParser.parse(ofx_file)
            for account in ofx.accounts:
                for tx in account.statement.transactions:
                    # Check if fitid already exists for this company
                    if Transaction.objects.filter(company=company, fitid=tx.id).exists():
                        continue
                        
                    amount = Decimal(str(tx.amount))
                    description = tx.memo or tx.payee or 'Imported OFX Transaction'
                    
                    category = auto_categorize_transaction(description, company)
                    
                    Transaction.objects.create(
                        company=company,
                        bank_account=bank_account,
                        category=category,
                        date=tx.date.date() if hasattr(tx.date, 'date') else tx.date,
                        description=description,
                        amount=abs(amount),
                        fitid=tx.id
                    )
        except Exception as e:
            # In a production environment we'd use the messages framework to show an error
            print(f"Error parsing OFX: {e}")
            
    return redirect('transactions')

@login_required
def pricing_calculator_view(request):
    """
    Smart Pricing Calculator that factors in Simples Nacional tax rates.
    Price = Cost / (1 - (Tax% + Fee% + Margin%))
    """
    company_user = request.user.companies.first()
    if not company_user:
        return redirect('dashboard')
    company = company_user.company
        
    current_month = datetime.today().month
    current_year = datetime.today().year
    
    # Get current tax rate (mock a small revenue to get the exact bracket aliquota)
    test_revenue = Decimal('100.00')
    tax_calc = calculate_monthly_das(company, current_month, current_year, test_revenue)
    current_tax_rate = tax_calc.aliquota_efetiva * 100
    
    context = {
        'current_tax_rate': current_tax_rate,
        'simulations': ProductPricing.objects.filter(company=company).order_by('-created_at')
    }
    
    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        base_cost = Decimal(request.POST.get('base_cost', '0'))
        gateway_fee_percent = Decimal(request.POST.get('gateway_fee_percent', '0'))
        desired_margin_percent = Decimal(request.POST.get('desired_margin_percent', '0'))
        
        # Calculate Final Price
        total_deductions_percent = (current_tax_rate + gateway_fee_percent + desired_margin_percent) / Decimal('100')
        
        if total_deductions_percent >= 1:
            context['error'] = "Total deductions (Tax + Fees + Margin) cannot exceed 100%!"
        else:
            final_price = base_cost / (Decimal('1') - total_deductions_percent)
            
            ProductPricing.objects.create(
                company=company,
                product_name=product_name,
                base_cost=base_cost,
                gateway_fee_percent=gateway_fee_percent,
                desired_margin_percent=desired_margin_percent,
                simples_nacional_rate=current_tax_rate,
                final_price=final_price
            )
            context['simulations'] = ProductPricing.objects.filter(company=company).order_by('-created_at')
            context['success'] = f"Simulation saved! Recommended Price for {product_name}: R$ {final_price:.2f}"
            
    return render(request, 'pricing_calculator.html', context)
