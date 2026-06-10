from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .services import update_company_health

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
        'is_critical': health_record.bankruptcy_risk_score > 60
    }
    
    return render(request, 'ai_dashboard.html', context)

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
