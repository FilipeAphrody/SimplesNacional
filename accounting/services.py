from decimal import Decimal
from django.db.models import Sum
from dateutil.relativedelta import relativedelta
from datetime import date
from accounting.models import RevenueRecord, TaxBracket, DASCalculation

def get_last_12_months_period(month, year):
    """Returns the start and end month/year for the 12 months prior to the given month/year."""
    current_date = date(year, month, 1)
    end_date = current_date - relativedelta(months=1)
    start_date = current_date - relativedelta(months=12)
    return start_date, end_date

def get_records_for_period(company, start_date, end_date):
    """Fetch revenue records between start_date and end_date (inclusive)."""
    # This is a bit tricky with month/year integers.
    # We'll fetch all records and filter in Python for simplicity, assuming few records.
    # Or we can reconstruct a date for filtering.
    records = RevenueRecord.objects.filter(company=company)
    valid_records = []
    for r in records:
        r_date = date(r.year, r.month, 1)
        if start_date <= r_date <= end_date:
            valid_records.append(r)
    return valid_records

def calculate_rbt12(company, month, year, current_month_revenue=Decimal('0.00')):
    """
    Calculates Receita Bruta Acumulada nos Últimos 12 Meses (RBT12).
    If the company has less than 12 months of operation, it calculates the proportional RBT12.
    """
    start_date, end_date = get_last_12_months_period(month, year)
    records = get_records_for_period(company, start_date, end_date)
    
    num_months_operating = len(records)
    
    if num_months_operating == 0:
        # First month of operation: RBT12 is the current month revenue * 12
        return current_month_revenue * 12
    elif num_months_operating < 12:
        # Proportional: (Sum of revenues / number of months) * 12
        total_revenue = sum(r.gross_revenue for r in records)
        return (total_revenue / num_months_operating) * 12
    else:
        # Full 12 months
        return sum(r.gross_revenue for r in records)

def calculate_fator_r(company, month, year, current_month_revenue=Decimal('0.00'), current_month_payroll=Decimal('0.00')):
    """
    Calculates the Fator 'r'.
    Fator r = Folha de Salários (last 12m) / Receita Bruta (last 12m)
    """
    start_date, end_date = get_last_12_months_period(month, year)
    records = get_records_for_period(company, start_date, end_date)
    
    num_months = len(records)
    
    if num_months == 0:
        rbt12 = current_month_revenue * 12
        folha12 = current_month_payroll * 12
    elif num_months < 12:
        rbt12 = (sum(r.gross_revenue for r in records) / num_months) * 12
        folha12 = (sum(r.payroll_expense for r in records) / num_months) * 12
    else:
        rbt12 = sum(r.gross_revenue for r in records)
        folha12 = sum(r.payroll_expense for r in records)
        
    if rbt12 == 0:
        return Decimal('0.00')
        
    return folha12 / rbt12

def get_effective_tax_rate(anexo, rbt12):
    """
    Calculates the effective tax rate (Alíquota Efetiva) for a given anexo and rbt12.
    formula: ((RBT12 * Aliquota Nominal) - Parcela a Deduzir) / RBT12
    """
    # Max RBT12 for Simples Nacional is generally 4,800,000.
    bracket = TaxBracket.objects.filter(
        anexo=anexo, 
        min_revenue__lte=rbt12, 
        max_revenue__gte=rbt12
    ).first()
    
    # Fallback to highest bracket if RBT12 exceeds the table (though they should be excluded from Simples)
    if not bracket:
        bracket = TaxBracket.objects.filter(anexo=anexo).order_by('-max_revenue').first()
        
    if not bracket or rbt12 == 0:
        return Decimal('0.00')
        
    # ((RBT12 * Aliquota Nominal) - Parcela a Deduzir) / RBT12
    aliquota_efetiva = ((rbt12 * bracket.aliquota_nominal) - bracket.parcela_deduzir) / rbt12
    
    # The effective rate cannot be negative.
    if aliquota_efetiva < 0:
        aliquota_efetiva = bracket.aliquota_nominal
        
    return aliquota_efetiva

def calculate_monthly_das(company, month, year, current_revenue, current_payroll=Decimal('0.00'), base_anexo='I', is_subject_to_fator_r=False):
    """
    Calculates the DAS for a specific month.
    """
    rbt12 = calculate_rbt12(company, month, year, current_revenue)
    
    applied_anexo = base_anexo
    fator_r = None
    
    if is_subject_to_fator_r:
        fator_r = calculate_fator_r(company, month, year, current_revenue, current_payroll)
        # If fator_r >= 0.28, Anexo III, else Anexo V
        if fator_r >= Decimal('0.28'):
            applied_anexo = 'III'
        else:
            applied_anexo = 'V'
            
    aliquota_efetiva = get_effective_tax_rate(applied_anexo, rbt12)
    das_amount = current_revenue * aliquota_efetiva
    
    das_calc, created = DASCalculation.objects.update_or_create(
        company=company,
        month=month,
        year=year,
        defaults={
            'rbt12': rbt12,
            'revenue_month': current_revenue,
            'anexo_applied': applied_anexo,
            'fator_r': fator_r,
            'aliquota_efetiva': aliquota_efetiva,
            'das_amount': das_amount
        }
    )
    
    return das_calc
