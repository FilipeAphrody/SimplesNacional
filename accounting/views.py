from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from decimal import Decimal
from datetime import date
from finance.models import Transaction
from accounting.models import DASCalculation

@login_required
def dre_report_view(request):
    company_user = request.user.companies.first()
    if not company_user:
        return redirect('dashboard')
    company = company_user.company

    # By default, show DRE for the current year
    year = int(request.GET.get('year', date.today().year))
    
    # 1. Receita Bruta (All Income)
    gross_revenue = Transaction.objects.filter(
        company=company,
        date__year=year,
        category__type='INCOME'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # 2. Impostos (DAS)
    # Get all DAS calculated for this year
    total_taxes = DASCalculation.objects.filter(
        company=company,
        year=year
    ).aggregate(total=Sum('das_amount'))['total'] or Decimal('0.00')

    # 3. Receita Líquida
    net_revenue = gross_revenue - total_taxes

    # 4. Despesas Operacionais (All Expenses)
    operating_expenses = Transaction.objects.filter(
        company=company,
        date__year=year,
        category__type='EXPENSE'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # 5. Lucro Líquido
    net_profit = net_revenue - operating_expenses

    # Detailed expenses breakdown by category
    expenses_breakdown = Transaction.objects.filter(
        company=company,
        date__year=year,
        category__type='EXPENSE'
    ).values('category__name').annotate(total=Sum('amount')).order_by('-total')

    context = {
        'year': year,
        'gross_revenue': f"{gross_revenue:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'total_taxes': f"{total_taxes:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'net_revenue': f"{net_revenue:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'operating_expenses': f"{operating_expenses:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'net_profit': f"{net_profit:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'expenses_breakdown': expenses_breakdown,
        'is_profit': net_profit >= 0,
    }
    
    return render(request, 'dre_report.html', context)
