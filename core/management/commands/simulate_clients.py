from django.core.management.base import BaseCommand
import os
import random
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from core.models import Company, CompanyUser
from finance.models import BankAccount, TransactionCategory, Transaction
from companies.models import CompanyProfile, CNAE
from ai.services import update_company_health

User = get_user_model()

PERSONAS = [
    {"name": "Tech Startup Ltda", "type": "startup", "revenue": (5000, 15000), "expenses": (10000, 20000), "b2b": True},
    {"name": "Boutique Moda SP", "type": "ecommerce", "revenue": (80000, 120000), "expenses": (50000, 70000), "b2b": False},
    {"name": "Dr. João Odonto", "type": "clinic", "revenue": (30000, 50000), "expenses": (5000, 15000), "b2b": False, "fator_r": True},
    {"name": "Agência Criativa", "type": "agency", "revenue": (40000, 60000), "expenses": (10000, 20000), "b2b": True},
    {"name": "Mecânica do Zé", "type": "disorganized", "revenue": (10000, 30000), "expenses": (15000, 35000), "b2b": False},
    {"name": "Sorveteria Verão", "type": "seasonal", "revenue": (5000, 40000), "expenses": (10000, 15000), "b2b": False},
    {"name": "Consultoria Alpha", "type": "consulting", "revenue": (15000, 25000), "expenses": (2000, 5000), "b2b": True},
    {"name": "Padaria Central", "type": "retail", "revenue": (50000, 70000), "expenses": (40000, 60000), "b2b": False},
    {"name": "Freelancer Dev", "type": "freelancer", "revenue": (8000, 15000), "expenses": (500, 2000), "b2b": True},
    {"name": "Clínica Médica Vida", "type": "clinic", "revenue": (100000, 150000), "expenses": (30000, 50000), "b2b": False, "fator_r": True},
    {"name": "Loja de Ferragens", "type": "retail", "revenue": (60000, 90000), "expenses": (55000, 85000), "b2b": True},
    {"name": "Petshop Cão Feliz", "type": "retail", "revenue": (20000, 35000), "expenses": (15000, 25000), "b2b": False},
    {"name": "Escola de Inglês", "type": "education", "revenue": (40000, 50000), "expenses": (20000, 30000), "b2b": False},
    {"name": "Restaurante Sabor", "type": "food", "revenue": (80000, 110000), "expenses": (70000, 100000), "b2b": False},
    {"name": "Marcenaria Silva", "type": "industry", "revenue": (30000, 60000), "expenses": (20000, 40000), "b2b": True},
    {"name": "Academia Fit", "type": "service", "revenue": (50000, 70000), "expenses": (30000, 50000), "b2b": False},
    {"name": "Transportadora Rápida", "type": "logistics", "revenue": (100000, 200000), "expenses": (90000, 180000), "b2b": True},
    {"name": "Salão de Beleza VIP", "type": "service", "revenue": (15000, 25000), "expenses": (10000, 15000), "b2b": False},
    {"name": "Estúdio de Pilates", "type": "clinic", "revenue": (20000, 30000), "expenses": (8000, 12000), "b2b": False, "fator_r": True},
    {"name": "Empresa Fictícia", "type": "disorganized", "revenue": (10000, 15000), "expenses": (12000, 20000), "b2b": True},
]

def generate_transactions(company, bank_account, income_cat, expense_cat, personal_cat, profile):
    today = date.today()
    transactions = []
    
    for i in range(180): # 6 months of data
        tx_date = today - timedelta(days=i)
        
        # Revenue
        daily_rev = Decimal(random.uniform(*profile['revenue'])) / 30
        if profile['type'] == 'seasonal' and tx_date.month in [12, 1, 2]:
            daily_rev *= 3
        
        # Add income
        if random.random() > 0.3:
            desc = "Nota Fiscal - B2B" if profile['b2b'] else "Venda Consumidor"
            transactions.append(Transaction(company=company, bank_account=bank_account, category=income_cat, date=tx_date, description=desc, amount=daily_rev))
        
        # Add expense
        daily_exp = Decimal(random.uniform(*profile['expenses'])) / 30
        if random.random() > 0.2:
            transactions.append(Transaction(company=company, bank_account=bank_account, category=expense_cat, date=tx_date, description="Fornecedor/Operacional", amount=-daily_exp))
            
        # Add personal mix for disorganized
        if profile['type'] == 'disorganized' and random.random() > 0.5:
            transactions.append(Transaction(company=company, bank_account=bank_account, category=personal_cat, date=tx_date, description=random.choice(["iFood", "Netflix", "Supermercado (Pessoal)"]), amount=Decimal("-150.00")))
            
    Transaction.objects.bulk_create(transactions)

class Command(BaseCommand):
    help = 'Runs 20 ICP personas simulation'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting ICP Simulation (20 Personas)...")
    
        # Setup base CNAEs
        cnae_service, _ = CNAE.objects.get_or_create(code="6201-5/01", defaults={"description": "Desenv. Software", "default_anexo": "III", "is_subject_to_fator_r": False})
        cnae_clinic, _ = CNAE.objects.get_or_create(code="8630-5/03", defaults={"description": "Atividade Médica", "default_anexo": "V", "is_subject_to_fator_r": True})

        feedback_log = []
        
        for idx, profile in enumerate(PERSONAS):
            self.stdout.write(f"[{idx+1}/20] Simulating {profile['name']}...")
            
            user_email = f"user_{idx}@simples.com"
            user, _ = User.objects.get_or_create(username=user_email, email=user_email)
            
            cnpj = f"{random.randint(10,99)}.000.000/0001-{random.randint(10,99)}"
            company = Company.objects.create(name=profile['name'], cnpj=cnpj)
            CompanyUser.objects.create(user=user, company=company, role='OWNER')
            
            CompanyProfile.objects.create(company=company, primary_cnae=cnae_clinic if profile.get('fator_r') else cnae_service)
            bank = BankAccount.objects.create(company=company, name="Conta PJ", initial_balance=Decimal("10000.00"))
            
            inc_cat = TransactionCategory.objects.create(company=company, name="Vendas", type="INCOME", is_simples_revenue=True)
            exp_cat = TransactionCategory.objects.create(company=company, name="Operacional", type="EXPENSE")
            pers_cat = TransactionCategory.objects.create(company=company, name="Pessoal (Misturado)", type="EXPENSE")
            
            generate_transactions(company, bank, inc_cat, exp_cat, pers_cat, profile)
            
            # Trigger AI Analysis
            try:
                metrics, insights = update_company_health(company)
                
                # Aggregate feedback based on what the AI noticed
                reaction = ""
                if "CRITICAL" in insights or "WARNING" in insights:
                    reaction = "Needs easier actionable steps. 'I see the warning, but what do I click to fix it?'"
                if "runway" in insights.lower() and metrics.runway_months < 3:
                    reaction = "Stressed about cash flow. AI was accurate but induced panic. Wants cash flow projection tools."
                if "fator r" in insights.lower() and metrics.payroll_ratio < 28:
                    reaction = "AMAZED! Didn't know they were overpaying taxes. Wants to hire someone immediately."
                if "personal expenses" in insights.lower():
                    reaction = "Embarrassed. System caught them mixing accounts. Good wake-up call, but needs UI to categorize personal vs PJ easily."
                
                feedback_log.append({
                    "persona": profile['name'],
                    "type": profile['type'],
                    "runway": f"{metrics.runway_months} months",
                    "risk": f"{metrics.risk_score}%",
                    "ai_feedback": reaction if reaction else "Happy. Everything is stable. Wants growth tools (marketing ROI)."
                })
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error simulating company: {e}"))
                 
        self.stdout.write(self.style.SUCCESS("Simulation Complete!"))
        
        # Save log to scratch for the agent to read
        os.makedirs('scratch', exist_ok=True)
        with open('scratch/simulation_results.txt', 'w', encoding='utf-8') as f:
            for fb in feedback_log:
                f.write(f"Persona: {fb['persona']} ({fb['type']})\n")
                f.write(f"Risk: {fb['risk']} | Runway: {fb['runway']}\n")
                f.write(f"User Feedback: {fb['ai_feedback']}\n")
                f.write("-" * 40 + "\n")
