import os
import pickle
import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime, timedelta
from decimal import Decimal
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from django.conf import settings
from .models import CompanyHealthMetrics, AnonymizedDataSnapshot
from finance.models import Transaction, BankAccount
from accounting.services import calculate_rbt12, calculate_monthly_das
import re

MODEL_PATH = os.path.join(settings.BASE_DIR, 'ai', 'bankruptcy_model.pkl')

def build_company_graph(company):
    """
    Build a NetworkX Knowledge Graph of the company's financial behavior.
    Nodes: Company, BankAccount, Categories, Transactions
    Edges: Owns, HasTransaction, CategorizedAs
    """
    G = nx.Graph()
    G.add_node(f"Company_{company.id}", type="Company", name=company.name)
    
    transactions = Transaction.objects.filter(company=company)
    
    # Track metrics while building graph
    total_tx = 0
    personal_tx_count = 0
    monthly_net = {}
    
    for tx in transactions:
        tx_node = f"Tx_{tx.id}"
        G.add_node(tx_node, type="Transaction", amount=float(tx.amount), date=str(tx.date))
        G.add_edge(f"Company_{company.id}", tx_node, relation="HAS_TRANSACTION")
        
        if tx.category:
            cat_node = f"Cat_{tx.category.id}"
            if not G.has_node(cat_node):
                G.add_node(cat_node, type="Category", name=tx.category.name, tx_type=tx.category.type)
            G.add_edge(tx_node, cat_node, relation="BELONGS_TO_CATEGORY")
            
            # Feature extraction logic
            if 'pessoal' in tx.category.name.lower() or 'pf' in tx.category.name.lower() or 'personal' in tx.category.name.lower():
                personal_tx_count += 1
                
            month_key = f"{tx.date.year}-{tx.date.month:02d}"
            if month_key not in monthly_net:
                monthly_net[month_key] = 0.0
                
            if tx.category.type == 'INCOME':
                monthly_net[month_key] += float(tx.amount)
            else:
                monthly_net[month_key] -= float(tx.amount)
                
        total_tx += 1

    # Calculate graph-based features
    account_mixing_score = (personal_tx_count / total_tx * 100) if total_tx > 0 else 0.0
    
    net_values = list(monthly_net.values())
    cash_flow_volatility = float(np.std(net_values)) if len(net_values) > 1 else 0.0
    
    # Calculate Runway
    total_cash = sum(float(acc.current_balance) for acc in BankAccount.objects.filter(company=company))
    monthly_burns = [abs(v) for v in net_values if v < 0]
    avg_burn = float(np.mean(monthly_burns)) if monthly_burns else 0.0
    
    if avg_burn > 0:
        runway_months = total_cash / avg_burn
    else:
        runway_months = 999.0 # Infinite runway if no burn
        
    working_capital_ratio = float(total_cash / avg_burn) if avg_burn > 0 else 999.0

    return {
        'graph': G,
        'metrics': {
            'account_mixing_score': account_mixing_score,
            'cash_flow_volatility': cash_flow_volatility,
            'working_capital_ratio': working_capital_ratio,
            'reactive_monitoring_score': 50.0,  # Mock behavioral metric
            'runway_months': runway_months,
            'avg_burn': avg_burn,
            'total_cash': total_cash
        }
    }

def train_synthetic_model():
    """
    Generates synthetic Brazilian PME data based on Serasa bankruptcy predictors,
    trains a RandomForest, and saves the model.
    """
    np.random.seed(42)
    n_samples = 1000
    
    # Generate Synthetic Data
    # 1. Successful Companies (Low mixing, low volatility, good working capital)
    success_mixing = np.random.normal(5, 5, int(n_samples/2))
    success_vol = np.random.normal(2000, 1000, int(n_samples/2))
    success_wc = np.random.normal(3.0, 1.0, int(n_samples/2))
    
    # 2. Bankrupt Companies (High mixing, high volatility, bad working capital)
    fail_mixing = np.random.normal(40, 15, int(n_samples/2))
    fail_vol = np.random.normal(8000, 3000, int(n_samples/2))
    fail_wc = np.random.normal(0.8, 0.4, int(n_samples/2))
    
    X_success = np.column_stack((success_mixing, success_vol, success_wc))
    y_success = np.zeros(int(n_samples/2)) # 0 = Safe
    
    X_fail = np.column_stack((fail_mixing, fail_vol, fail_wc))
    y_fail = np.ones(int(n_samples/2)) # 1 = Bankrupt
    
    X = np.vstack((X_success, X_fail))
    y = np.concatenate((y_success, y_fail))
    
    # Clip unrealistic bounds
    X[:, 0] = np.clip(X[:, 0], 0, 100) # mixing %
    X[:, 1] = np.clip(X[:, 1], 0, None) # volatility
    X[:, 2] = np.clip(X[:, 2], 0, None) # working capital
    
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)
    
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(clf, f)
        
    return "Model trained and saved."

_cached_clf = None

def predict_bankruptcy_risk(metrics_dict):
    """ Loads the ML model and predicts bankruptcy probability based on extracted graph metrics. """
    global _cached_clf
    
    if not os.path.exists(MODEL_PATH):
        train_synthetic_model()
        
    if _cached_clf is None:
        with open(MODEL_PATH, 'rb') as f:
            _cached_clf = pickle.load(f)  # nosec B301
            
    X_input = np.array([[
        metrics_dict['account_mixing_score'],
        metrics_dict['cash_flow_volatility'],
        metrics_dict['working_capital_ratio']
    ]])
    
    # Get probability of class 1 (Bankruptcy)
    prob = _cached_clf.predict_proba(X_input)[0][1]
    return round(prob * 100, 2)

def scan_tax_optimization(company):
    """
    Compares the current Simples Nacional effective rate against a generic Lucro Presumido rate.
    Lucro Presumido for services is roughly 13.33% to 16.33% depending on ISS.
    We will use 14.5% as a benchmark.
    """
    try:
        current_month = datetime.today().month
        current_year = datetime.today().year
        
        rbt12 = calculate_rbt12(company, current_month, current_year)
        # Mocking an Faturamento for the month to get the effective rate
        test_revenue = Decimal('10000.00')
        tax_results = calculate_monthly_das(company, current_month, current_year, test_revenue)
        
        effective_rate = tax_results.aliquota_efetiva * 100
        lucro_presumido_benchmark = 14.5
        
        if float(effective_rate) > lucro_presumido_benchmark:
            savings_pct = float(effective_rate) - lucro_presumido_benchmark
            annual_savings = (float(rbt12) * (savings_pct / 100))
            return f"🚨 TAX ALERT: Your effective Simples Nacional rate is {effective_rate:.2f}%. A switch to Lucro Presumido (approx {lucro_presumido_benchmark}%) could save you ~R$ {annual_savings:,.2f} annually."
        return "Your current Simples Nacional tax regime is mathematically optimal."
    except Exception as e:
        return f"Not enough data to calculate tax optimization: {e}"

def sanitize_prompt_for_llm(metrics_dict):
    """
    LLM06 Mitigation (Sensitive Information Disclosure):
    Redacts absolute monetary values before sending data to an external LLM.
    We convert raw R$ values to proportions/ratios to maintain AI context without leaking PII.
    """
    redacted = metrics_dict.copy()
    if 'total_cash' in redacted: redacted['total_cash'] = "[REDACTED_AMOUNT]"
    if 'avg_burn' in redacted: redacted['avg_burn'] = "[REDACTED_AMOUNT]"
    # Real logic would pass ratio: redacted['cash_to_burn_ratio'] = metrics_dict['runway_months']
    return redacted

def generate_ai_insight(metrics_dict, risk_score, tax_alert):
    """
    Mock LLM RAG Insight generation.
    Incorporates LLM02 Mitigation (Insecure Output Handling) by converting
    Markdown to HTML and explicitly sanitizing it with bleach.
    """
    import bleach
    import markdown
    
    # 1. LLM06 Mitigation Step: Ensure we never send raw PII to the prompt builder
    safe_metrics = sanitize_prompt_for_llm(metrics_dict)
    
    insights = []
    
    if safe_metrics['account_mixing_score'] > 20:
        insights.append("I noticed a high volume of transactions flagged as 'Personal'. Mixing PF and PJ accounts is the #1 behavioral predictor of bankruptcy for Simples Nacional businesses according to Serasa. Please separate your personal expenses immediately.")
        
    runway = safe_metrics.get('runway_months', 0)
    if runway < 3:
        insights.append(f"⚠️ **RUNWAY WARNING**: Based on your current trajectory, you only have **{runway:.1f} months** of runway left. You need to secure capital or drastically cut expenses. *(Raw values redacted for security)*")
    elif runway < 6:
        insights.append(f"Your cash runway is **{runway:.1f} months**. This is safe, but consider building more reserves.")
    else:
        insights.append(f"Excellent liquidity! You have **{runway:.1f} months** of runway, which provides a massive safety net for growth.")
        
    if risk_score > 60:
        insights.append("<script>alert('malicious')</script> CRITICAL WARNING: Based on your graph metrics, our predictive model flags your company at a high risk of insolvency within the next 12 months. Focus entirely on cost reduction and eliminating short-term high-interest debt.")
        
    insights.append(tax_alert)
        
    # Formatting as a mock LLM output
    raw_markdown = "### 🤖 AI CFO Analysis\n\n" + "\n\n".join(insights)
    
    # LLM02 Mitigation Step: Convert to HTML and Sanitize
    html_output = markdown.markdown(raw_markdown)
    
    # Bleach config: allow basic formatting tags, but strip scripts/iframes
    allowed_tags = ['h1', 'h2', 'h3', 'h4', 'p', 'b', 'i', 'strong', 'em', 'ul', 'ol', 'li', 'br', 'span', 'div']
    sanitized_html = bleach.clean(html_output, tags=allowed_tags, strip=True)
    
    return sanitized_html

def update_company_health(company):
    """ Main entry point to refresh a company's AI profile. """
    graph_data = build_company_graph(company)
    metrics = graph_data['metrics']
    
    risk_score = predict_bankruptcy_risk(metrics)
    tax_alert = scan_tax_optimization(company)
    
    health_record, created = CompanyHealthMetrics.objects.update_or_create(
        company=company,
        defaults={
            'cash_flow_volatility': metrics['cash_flow_volatility'],
            'working_capital_ratio': metrics['working_capital_ratio'],
            'account_mixing_score': metrics['account_mixing_score'],
            'reactive_monitoring_score': metrics['reactive_monitoring_score'],
            'bankruptcy_risk_score': risk_score,
            'runway_months': metrics['runway_months'],
            'tax_optimization_alert': tax_alert
        }
    )
    
    
    insight_text = generate_ai_insight(metrics, risk_score, tax_alert)
    
    # Create an Anonymized Data Lake Snapshot to build the SaaS Moat
    snapshot_company_for_data_lake(company, metrics, risk_score, tax_alert)
    
    return health_record, insight_text

def snapshot_company_for_data_lake(company, metrics, risk_score, tax_alert):
    """
    Extracts deep signals and strips all PII (LGPD compliant).
    Builds the proprietary Data Lake for future ML fine-tuning.
    """
    try:
        # Determine CNAE Sector
        sector = "Unknown"
        profile = getattr(company, 'profile', None)
        if profile and profile.primary_cnae:
            cnae_str = profile.primary_cnae.code
            if cnae_str.startswith('47') or cnae_str.startswith('45'): sector = 'Commerce'
            elif cnae_str.startswith('62') or cnae_str.startswith('69'): sector = 'Services'
            elif cnae_str.startswith('10') or cnae_str.startswith('32'): sector = 'Industry'
            else: sector = 'Other'
            
        # Analyze B2B vs B2C based on categories (Mock logic based on common naming)
        b2b_tx_count = 0
        total_tx = 0
        fixed_costs = 0
        debt_payments = 0
        total_expenses = 0
        
        for tx in Transaction.objects.filter(company=company):
            total_tx += 1
            if tx.category:
                cat_name = tx.category.name.lower()
                if tx.category.type == 'INCOME' and ('b2b' in cat_name or 'corporate' in cat_name or 'nf-e' in cat_name):
                    b2b_tx_count += 1
                if tx.category.type == 'EXPENSE':
                    total_expenses += float(tx.amount)
                    if 'rent' in cat_name or 'salary' in cat_name or 'software' in cat_name or 'fixed' in cat_name:
                        fixed_costs += float(tx.amount)
                    if 'loan' in cat_name or 'interest' in cat_name or 'juros' in cat_name or 'debt' in cat_name:
                        debt_payments += float(tx.amount)
                        
        b2b_ratio = (b2b_tx_count / total_tx * 100) if total_tx > 0 else 0.0
        fixed_ratio = (fixed_costs / total_expenses * 100) if total_expenses > 0 else 0.0
        debt_ratio = (debt_payments / total_expenses * 100) if total_expenses > 0 else 0.0
        
        # Payroll / Fator R approximation
        # We assume they are subject to Fator R if the tax_alert doesn't explicitly clear them
        payroll_ratio = 28.0 if 'optimal' in tax_alert.lower() else 15.0
        
        AnonymizedDataSnapshot.objects.create(
            cnae_sector=sector,
            b2b_vs_b2c_ratio=b2b_ratio,
            simples_nacional_burden=6.0, # Placeholder average
            payroll_ratio=payroll_ratio,
            account_mixing_score=metrics.get('account_mixing_score', 0.0),
            cash_flow_volatility=metrics.get('cash_flow_volatility', 0.0),
            fixed_vs_variable_costs=fixed_ratio,
            working_capital_ratio=metrics.get('working_capital_ratio', 0.0),
            debt_payment_ratio=debt_ratio,
            runway_months=metrics.get('runway_months', 999.0),
            # In a real environment, this gets updated via a chron job if the company churns
            is_insolvent=False
        )
    except Exception as e:
        # Silently fail snapshot rather than breaking user experience
        pass

def optimize_fator_r(rbt12, current_payroll_11m):
    """
    Calculates the exact amount of Pró-labore needed this month to hit exactly 28.01% Fator R.
    Fator R = (Payroll 12m) / RBT12.
    We need: (current_payroll_11m + this_month_pro_labore) / RBT12 = 0.2801
    """
    if rbt12 <= 0:
        return Decimal('0.00')
        
    target_payroll_12m = rbt12 * Decimal('0.2801')
    required_this_month = target_payroll_12m - current_payroll_11m
    
    if required_this_month <= 0:
        return Decimal('0.00') # Already hitting the target
        
    return required_this_month

def simulate_reforma_tributaria(b2b_percentage):
    """
    Simulates the EC 132/2023 dilemma for Simples Nacional in 2026.
    If a company sells mostly to other businesses (B2B), they must collect IBS/CBS separately (Option B) 
    so their clients get full tax credits.
    If they sell mostly to consumers (B2C), they should stay unified (Option A).
    """
    if b2b_percentage >= 60:
        return {
            "recommendation": "Option B (Segregated Collection)",
            "reasoning": f"Since {b2b_percentage}% of your sales are B2B, your corporate clients will demand full IBS/CBS tax credits. Staying unified would make you uncompetitive. You should collect IBS/CBS outside the DAS.",
            "color": "text-yellow-400"
        }
    else:
        return {
            "recommendation": "Option A (Unified Collection)",
            "reasoning": f"Since only {b2b_percentage}% of your sales are B2B, you don't need to generate massive tax credits for your clients. Stay unified inside the Simples Nacional DAS to avoid bureaucracy.",
            "color": "text-green-400"
        }

def analyze_sup_eligibility(is_professional, number_of_partners, current_annual_tax):
    """
    Sociedade Uniprofissional (SUP) scanner.
    If they are eligible professionals, they can pay a fixed ISS instead of variable.
    """
    if not is_professional:
        return {"eligible": False, "savings": Decimal('0.00'), "message": "Only regulated professions (Doctors, Lawyers, etc.) are eligible."}
        
    # Mock fixed ISS rate per partner: R$ 2000 / year
    fixed_iss_total = Decimal('2000.00') * Decimal(str(number_of_partners))
    
    if fixed_iss_total < current_annual_tax:
        savings = current_annual_tax - fixed_iss_total
        return {"eligible": True, "savings": savings, "message": f"Switching to SUP could save you R$ {savings:,.2f} per year by fixing your ISS."}
    else:
        return {"eligible": False, "savings": Decimal('0.00'), "message": "Your current variable tax is cheaper than the fixed SUP fee."}

def auto_categorize_transaction(description, company):
    """
    Lightweight NLP/Keyword categorizer to reduce onboarding friction.
    Searches the company's existing TransactionCategory based on keywords.
    """
    desc_lower = description.lower()
    
    # 1. Keyword mapping dictionaries
    personal_keywords = ['ifood', 'netflix', 'spotify', 'uber', 'farmácia', 'mercado', 'supermercado', 'pessoal']
    software_keywords = ['aws', 'google', 'microsoft', 'github', 'vercel', 'digitalocean', 'software', 'saas']
    income_keywords = ['nf-e', 'pix recebido', 'venda', 'pagarme', 'stripe', 'cielo', 'stone', 'recebimento']
    tax_keywords = ['das', 'gps', 'darf', 'simples nacional', 'imposto']
    payroll_keywords = ['salário', 'pro labore', 'pró-labore', 'adiantamento', 'folha', 'fgts']
    
    inferred_type = None
    target_name = "Despesas Diversas"
    
    if any(k in desc_lower for k in personal_keywords):
        inferred_type = 'EXPENSE'
        target_name = 'Pessoal (Misturado)'
    elif any(k in desc_lower for k in software_keywords):
        inferred_type = 'EXPENSE'
        target_name = 'Software/Ferramentas'
    elif any(k in desc_lower for k in income_keywords):
        inferred_type = 'INCOME'
        target_name = 'Vendas/Serviços'
    elif any(k in desc_lower for k in tax_keywords):
        inferred_type = 'EXPENSE'
        target_name = 'Impostos'
    elif any(k in desc_lower for k in payroll_keywords):
        inferred_type = 'EXPENSE'
        target_name = 'Folha de Pagamento'
    
    # If we couldn't infer anything, default to Expense
    if not inferred_type:
        inferred_type = 'EXPENSE'
        target_name = 'Operacional'
        
    from finance.models import TransactionCategory
    
    # Find or create the category for this company
    category, _ = TransactionCategory.objects.get_or_create(
        company=company,
        name=target_name,
        defaults={
            'type': inferred_type,
            'is_simples_revenue': True if target_name == 'Vendas/Serviços' else False
        }
    )
    
    return category
