from django.db import models
from core.models import Company

class RevenueRecord(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='revenue_records')
    month = models.IntegerField(help_text="1-12")
    year = models.IntegerField(help_text="e.g. 2026")
    gross_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Faturamento Bruto")
    payroll_expense = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Folha de Pagamentos (for Fator r)")

    class Meta:
        unique_together = ('company', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.company.name} - {self.month:02d}/{self.year}: {self.gross_revenue}"

class TaxBracket(models.Model):
    # Represents the tables for Anexo I, II, III, IV, V
    anexo = models.CharField(max_length=5)
    faixa = models.IntegerField(help_text="1 to 6")
    min_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    max_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    aliquota_nominal = models.DecimalField(max_digits=5, decimal_places=4, help_text="e.g. 0.0400 for 4%")
    parcela_deduzir = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('anexo', 'faixa')
        ordering = ['anexo', 'faixa']

    def __str__(self):
        return f"{self.anexo} - Faixa {self.faixa}"

class DASCalculation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='das_calculations')
    month = models.IntegerField(help_text="1-12")
    year = models.IntegerField()
    
    rbt12 = models.DecimalField(max_digits=12, decimal_places=2, help_text="Receita Bruta 12 Meses")
    revenue_month = models.DecimalField(max_digits=12, decimal_places=2)
    
    anexo_applied = models.CharField(max_length=5)
    fator_r = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    
    aliquota_efetiva = models.DecimalField(max_digits=7, decimal_places=6)
    das_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'month', 'year')

    def __str__(self):
        return f"DAS {self.company.name} - {self.month:02d}/{self.year}: {self.das_amount}"
