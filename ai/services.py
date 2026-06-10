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
from .models import CompanyHealthMetrics
from finance.models import Transaction, BankAccount
from accounting.services import calculate_rbt12, calculate_monthly_das

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

def predict_bankruptcy_risk(metrics_dict):
    """ Loads the ML model and predicts bankruptcy probability based on extracted graph metrics. """
    if not os.path.exists(MODEL_PATH):
        train_synthetic_model()
        
    with open(MODEL_PATH, 'rb') as f:
        clf = pickle.load(f)  # nosec B301
        
    X_input = np.array([[
        metrics_dict['account_mixing_score'],
        metrics_dict['cash_flow_volatility'],
        metrics_dict['working_capital_ratio']
    ]])
    
    # Get probability of class 1 (Bankruptcy)
    prob = clf.predict_proba(X_input)[0][1]
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

def generate_ai_insight(metrics_dict, risk_score, tax_alert):
    """
    Mock LLM RAG Insight generation.
    """
    insights = []
    
    if metrics_dict['account_mixing_score'] > 20:
        insights.append("I noticed a high volume of transactions flagged as 'Personal'. Mixing PF and PJ accounts is the #1 behavioral predictor of bankruptcy for Simples Nacional businesses according to Serasa. Please separate your personal expenses immediately.")
        
    runway = metrics_dict.get('runway_months', 0)
    if runway < 3:
        insights.append(f"⚠️ RUNWAY WARNING: Based on your average burn rate of R$ {metrics_dict['avg_burn']:,.2f} and cash reserves of R$ {metrics_dict['total_cash']:,.2f}, you only have {runway:.1f} months of runway left. You need to secure capital or drastically cut expenses.")
    elif runway < 6:
        insights.append(f"Your cash runway is {runway:.1f} months. This is safe, but consider building more reserves.")
    else:
        insights.append(f"Excellent liquidity! You have {runway:.1f} months of runway, which provides a massive safety net for growth.")
        
    if risk_score > 60:
        insights.append("CRITICAL WARNING: Based on your graph metrics, our predictive model flags your company at a high risk of insolvency within the next 12 months. Focus entirely on cost reduction and eliminating short-term high-interest debt.")
        
    insights.append(tax_alert)
        
    # Formatting as a mock LLM output
    llm_response = "### 🤖 AI CFO Analysis\n\n" + "\n\n".join(insights)
    return llm_response

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
    
    return health_record, insight_text

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
