from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import models
from decimal import Decimal
from datetime import date
from accounting.services import calculate_monthly_das, calculate_rbt12
from finance.models import Transaction, TransactionCategory

@login_required
def dashboard_view(request):
    company_user = request.user.companies.first()
    if not company_user:
        # In a full app, we'd redirect to a "Create Company" onboarding flow
        return render(request, 'dashboard_empty.html')
        
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
