from django.db import models
from core.models import Company

class CompanyHealthMetrics(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='health_metrics')
    last_updated = models.DateTimeField(auto_now=True)
    
    # Financial Metrics (from Sebrae/Serasa research)
    cash_flow_volatility = models.FloatField(default=0.0, help_text="Variance in monthly net profit")
    working_capital_ratio = models.FloatField(default=0.0, help_text="Cash reserves / Average monthly expenses")
    
    # Behavioral Metrics
    account_mixing_score = models.FloatField(default=0.0, help_text="Percentage of transactions marked as Personal/PF")
    reactive_monitoring_score = models.FloatField(default=0.0, help_text="Calculated based on login frequency vs transaction volume")
    
    # AI Predictive Output
    bankruptcy_risk_score = models.FloatField(null=True, blank=True, help_text="0-100 probability of bankruptcy in 12 months")
    runway_months = models.FloatField(null=True, blank=True, help_text="Months left before cash runs out")
    tax_optimization_alert = models.TextField(null=True, blank=True, help_text="Alert if Lucro Presumido is cheaper")
    
    def __str__(self):
        return f"Health Metrics for {self.company.name} - Risk: {self.bankruptcy_risk_score}%"

import uuid

class AnonymizedDataSnapshot(models.Model):
    """
    The Data Lake table. Contains NO foreign keys to preserve anonymity (LGPD compliance).
    This serves as the foundation for the "Moat", gathering deep signals across all SaaS clients.
    """
    snapshot_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Market & Structural Signals
    cnae_sector = models.CharField(max_length=100, null=True, blank=True)
    b2b_vs_b2c_ratio = models.FloatField(default=0.0, help_text="% of B2B transactions")
    simples_nacional_burden = models.FloatField(default=0.0, help_text="% of revenue spent on DAS")
    payroll_ratio = models.FloatField(default=0.0, help_text="Fator R payroll-to-revenue ratio")
    
    # Financial & Behavioral Signals
    account_mixing_score = models.FloatField(default=0.0)
    cash_flow_volatility = models.FloatField(default=0.0)
    fixed_vs_variable_costs = models.FloatField(default=0.0, help_text="% of expenses that are fixed")
    working_capital_ratio = models.FloatField(default=0.0)
    debt_payment_ratio = models.FloatField(default=0.0, help_text="% of expenses going to debt/loans")
    runway_months = models.FloatField(default=999.0)
    
    # Target Variable for ML
    is_insolvent = models.BooleanField(default=False, help_text="Did the company go bankrupt / fail?")

    def __str__(self):
        return f"Snapshot {self.snapshot_id} - Sector: {self.cnae_sector}"
