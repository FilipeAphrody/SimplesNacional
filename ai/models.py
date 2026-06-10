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
