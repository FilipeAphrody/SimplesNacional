from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models
from decimal import Decimal
from datetime import date
from accounting.services import calculate_monthly_das, calculate_rbt12
from finance.models import Transaction, TransactionCategory
from .models import Company, CompanyUser, SystemErrorLog

@login_required
def dashboard_view(request):
    company_user = request.user.companies.first()
    if not company_user:
        return redirect('onboarding')
        
    company = company_user.company
    
    # Get current month/year
    today = date.today()
    month = today.month
    year = today.year
    
    # For a real SaaS, we would calculate this based on the current month's actual logged revenue.
    # We will simulate the current month's revenue dynamically by summing Income transactions
    # marked as is_simples_revenue.
    current_revenue = Transaction.objects.filter(
        company=company,
        date__year=year,
        date__month=month,
        category__is_simples_revenue=True,
        category__type='INCOME'
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    # Get CNAE details to know if we need Fator r
    profile = getattr(company, 'profile', None)
    is_subject_to_fator_r = False
    base_anexo = 'III'
    if profile and profile.primary_cnae:
        is_subject_to_fator_r = profile.primary_cnae.is_subject_to_fator_r
        base_anexo = profile.primary_cnae.default_anexo

    # Calculate DAS
    das_calc = calculate_monthly_das(
        company=company,
        month=month,
        year=year,
        current_revenue=current_revenue,
        base_anexo=base_anexo,
        is_subject_to_fator_r=is_subject_to_fator_r
    )

    # Get recent transactions
    recent_transactions = Transaction.objects.filter(company=company).order_by('-date')[:5]

    context = {
        'company': company,
        'rbt12': f"{das_calc.rbt12:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'current_anexo': das_calc.anexo_applied,
        'das_amount': f"{das_calc.das_amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'effective_rate': f"{(das_calc.aliquota_efetiva * 100):.2f}",
        'fator_r': f"{das_calc.fator_r:.2f}" if das_calc.fator_r is not None else '-',
        'recent_transactions': recent_transactions,
        # Chart data
        'revenue_labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'revenue_data': [12000, 15000, 14000, 18000, 22000, float(current_revenue)],
    }
    return render(request, 'dashboard.html', context)

@login_required
def onboarding_view(request):
    """ Allows a new user to register their company (mocking Receita Federal lookup). """
    if request.user.companies.exists():
        return redirect('dashboard')
        
    if request.method == 'POST':
        cnpj = request.POST.get('cnpj')
        name = request.POST.get('name')
        if cnpj and name:
            company = Company.objects.create(cnpj=cnpj, name=name)
            CompanyUser.objects.create(user=request.user, company=company, role='OWNER')
            return redirect('dashboard')
            
    return render(request, 'onboarding.html')

@user_passes_test(lambda u: u.is_superuser)
def superadmin_dashboard_view(request):
    """ High-security dashboard for SaaS owner to track clients and errors. """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    total_users = User.objects.count()
    total_companies = Company.objects.count()
    recent_errors = SystemErrorLog.objects.order_by('-created_at')[:10]
    companies = Company.objects.all().order_by('-created_at')
    
    # Deleted data recovery
    deleted_transactions = Transaction.all_objects.filter(is_deleted=True).order_by('-deleted_at')
    
    context = {
        'total_users': total_users,
        'total_companies': total_companies,
        'recent_errors': recent_errors,
        'companies': companies,
        'deleted_transactions': deleted_transactions
    }
    return render(request, 'superadmin.html', context)

@user_passes_test(lambda u: u.is_superuser)
def restore_transaction_view(request, tx_id):
    """ Superadmin endpoint to instantly restore accidentally deleted client data. """
    try:
        tx = Transaction.all_objects.get(id=tx_id, is_deleted=True)
        tx.restore()
    except Transaction.DoesNotExist:
        pass
    return redirect('superadmin')
