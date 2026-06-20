from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.db import models
from decimal import Decimal
from datetime import date
import csv
from accounting.services import calculate_monthly_das, calculate_rbt12
from finance.models import Transaction, TransactionCategory
from .models import Company, CompanyUser, SystemErrorLog
from ai.models import AnonymizedDataSnapshot

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

    # Chart data
    historical_data = [12000, 15000, 14000, 18000, 22000, float(current_revenue)]
    avg = sum(historical_data[-3:]) / 3
    predictive_data = [None] * 5 + [float(current_revenue), float(Decimal(str(avg))*Decimal('1.05')), float(Decimal(str(avg))*Decimal('1.02')), float(Decimal(str(avg))*Decimal('1.08'))]

    context = {
        'company': company,
        'rbt12': f"{das_calc.rbt12:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'current_anexo': das_calc.anexo_applied,
        'das_amount': f"{das_calc.das_amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'effective_rate': f"{(das_calc.aliquota_efetiva * 100):.2f}",
        'fator_r': f"{das_calc.fator_r:.2f}" if das_calc.fator_r is not None else '-',
        'recent_transactions': recent_transactions,
        'revenue_labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul (Pred)', 'Aug (Pred)', 'Sep (Pred)'],
        'revenue_data': historical_data + [None, None, None],
        'predictive_data': predictive_data,
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
    deleted_companies = Company.all_objects.filter(is_deleted=True).order_by('-deleted_at')
    deleted_categories = TransactionCategory.all_objects.filter(is_deleted=True).order_by('-deleted_at')
    
    context = {
        'total_users': total_users,
        'total_companies': total_companies,
        'recent_errors': recent_errors,
        'companies': companies,
        'deleted_transactions': deleted_transactions,
        'deleted_companies': deleted_companies,
        'deleted_categories': deleted_categories,
    }
    return render(request, 'superadmin.html', context)

@user_passes_test(lambda u: u.is_superuser)
def restore_transaction_view(request, tx_id):
    try:
        tx = Transaction.all_objects.get(id=tx_id, is_deleted=True)
        tx.restore()
    except Transaction.DoesNotExist:
        pass
    return redirect('superadmin')

@user_passes_test(lambda u: u.is_superuser)
def restore_company_view(request, company_id):
    try:
        comp = Company.all_objects.get(id=company_id, is_deleted=True)
        comp.restore()
    except Company.DoesNotExist:
        pass
    return redirect('superadmin')

@user_passes_test(lambda u: u.is_superuser)
def restore_category_view(request, cat_id):
    try:
        cat = TransactionCategory.all_objects.get(id=cat_id, is_deleted=True)
        cat.restore()
    except TransactionCategory.DoesNotExist:
        pass
    return redirect('superadmin')

@user_passes_test(lambda u: u.is_superuser)
def export_ai_dataset_view(request):
    """
    Superadmin endpoint to dump the Anonymized Data Lake into a CSV.
    This is used to fine-tune the Random Forest ML model.
    """
    SystemErrorLog.objects.create(
        status='RESOLVED',
        message=f"AUDIT: AI Data Moat exported by {request.user.username}"
    )
    
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="ai_moat_dataset.csv"'},
    )

    writer = csv.writer(response)
    # Write header
    writer.writerow([
        'cnae_sector', 'b2b_vs_b2c_ratio', 'simples_nacional_burden', 'payroll_ratio',
        'account_mixing_score', 'cash_flow_volatility', 'fixed_vs_variable_costs',
        'working_capital_ratio', 'debt_payment_ratio', 'runway_months', 'is_insolvent'
    ])

    for row in AnonymizedDataSnapshot.objects.all():
        writer.writerow([
            row.cnae_sector,
            row.b2b_vs_b2c_ratio,
            row.simples_nacional_burden,
            row.payroll_ratio,
            row.account_mixing_score,
            row.cash_flow_volatility,
            row.fixed_vs_variable_costs,
            row.working_capital_ratio,
            row.debt_payment_ratio,
            row.runway_months,
            int(row.is_insolvent)
        ])

    return response

@login_required
def reforma_simulator_view(request):
    """ Interactive UI for the EC 132/2023 Reforma Tributária dilemma. """
    from ai.services import simulate_reforma_tributaria
    company_user = request.user.companies.first()
    if not company_user:
        return redirect('dashboard')
        
    context = {}
    if request.method == 'POST':
        b2b_percentage = float(request.POST.get('b2b_percentage', 0))
        result = simulate_reforma_tributaria(b2b_percentage)
        context['b2b_percentage'] = b2b_percentage
        context['recommendation'] = result['recommendation']
        context['reasoning'] = result['reasoning']
        context['color'] = result['color']
        
    return render(request, 'reforma_simulator.html', context)
