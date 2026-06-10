from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import CompanyHealthMetrics
from .services import update_company_health, optimize_fator_r, simulate_reforma_tributaria, analyze_sup_eligibility
from accounting.services import calculate_rbt12

@login_required
def ai_dashboard_view(request):
    company_user = request.user.companies.first()
    if not company_user:
        return redirect('dashboard')
    company = company_user.company

    # This updates the metrics graph, calculates the risk score, and generates the LLM prompt
    health_record, insight_text = update_company_health(company)

    context = {
        'company': company,
        'metrics': health_record,
        'insight_text': insight_text,
        'is_critical': health_record.bankruptcy_risk_score > 60,
        'insight': health_record.tax_optimization_alert if health_record else "Not enough data for insights."
    }
    
    return render(request, 'ai_dashboard.html', context)

@login_required
def tax_engineering_view(request):
    company_user = request.user.companies.first()
    if not company_user:
        return redirect('dashboard')
    company = company_user.company
    
    # Defaults
    rbt12 = Decimal('100000.00') # Mock RBT12
    current_payroll_11m = Decimal('20000.00') # Mock current payroll
    current_annual_tax = Decimal('6000.00')
    
    # 1. Fator R Optimization
    required_pro_labore = optimize_fator_r(rbt12, current_payroll_11m)
    current_fator_r = (current_payroll_11m / rbt12) * 100 if rbt12 > 0 else 0
    
    # 2. Reforma Tributaria (default B2B = 30%)
    b2b_percentage = 30
    if request.method == 'POST' and 'b2b_percentage' in request.POST:
        b2b_percentage = int(request.POST.get('b2b_percentage', 30))
        
    reform_result = simulate_reforma_tributaria(b2b_percentage)
    
    # 3. SUP Scanner
    sup_result = analyze_sup_eligibility(True, 2, current_annual_tax)
    
    context = {
        'company': company,
        'rbt12': rbt12,
        'current_fator_r': current_fator_r,
        'required_pro_labore': required_pro_labore,
        'b2b_percentage': b2b_percentage,
        'reform_result': reform_result,
        'sup_result': sup_result
    }
    
    return render(request, 'tax_engineering.html', context)

@login_required
def ai_chat_api(request):
    """
    Mocked LLM Chat endpoint.
    """
    import json
    from django.http import JsonResponse
    
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '').lower()
        
        # Simple mocked intent matching for demonstration
        if 'runway' in user_message or 'cash' in user_message:
            reply = "Based on your current burn rate and bank balances, your cash runway is projected. If you delay your accounts payable by 15 days, you can extend your runway by 1.2 months."
        elif 'tax' in user_message or 'simples' in user_message:
            reply = "I am constantly monitoring your tax brackets. Your Simples Nacional effective rate is currently lower than Lucro Presumido, so you are in the optimal regime. If your revenue crosses R$ 1.8M, we will need to re-evaluate."
        elif 'margin' in user_message or 'profit' in user_message:
            reply = "Your profit margin dropped slightly this month due to an increase in 'Software Subscriptions'. I recommend auditing your SaaS licenses."
        else:
            reply = "That's a great question. As your AI CFO, I am analyzing your graph data to give you the best strategic advice. (This is a mock response — integrate an OpenAI/Gemini API key here to enable dynamic chat!)"
            
        return JsonResponse({'reply': reply})
        
    return JsonResponse({'error': 'Invalid request'}, status=400)
