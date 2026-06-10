from django.db import models
from core.models import Company

class CNAE(models.Model):
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    is_subject_to_fator_r = models.BooleanField(default=False)
    default_anexo = models.CharField(max_length=5, choices=(
        ('I', 'Anexo I - Comércio'),
        ('II', 'Anexo II - Indústria'),
        ('III', 'Anexo III - Serviços'),
        ('IV', 'Anexo IV - Serviços'),
        ('V', 'Anexo V - Serviços'),
    ))

    def __str__(self):
        return f"{self.code} - {self.description}"

class CompanyProfile(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='profile')
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=2, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)
    primary_cnae = models.ForeignKey(CNAE, on_delete=models.SET_NULL, null=True, related_name='primary_companies')
    secondary_cnaes = models.ManyToManyField(CNAE, blank=True, related_name='secondary_companies')

    def __str__(self):
        return f"Profile of {self.company.name}"

class SimplesNacionalHistory(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='simples_nacional_history')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    anexo = models.CharField(max_length=5, choices=(
        ('I', 'Anexo I'),
        ('II', 'Anexo II'),
        ('III', 'Anexo III'),
        ('IV', 'Anexo IV'),
        ('V', 'Anexo V'),
    ))

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.company.name} - {self.anexo} (Since {self.start_date})"
