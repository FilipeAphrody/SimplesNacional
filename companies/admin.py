from django.contrib import admin
from .models import CNAE, CompanyProfile

@admin.register(CNAE)
class CNAEAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'default_anexo', 'is_subject_to_fator_r')
    list_filter = ('default_anexo', 'is_subject_to_fator_r')
    search_fields = ('code', 'description')

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('company', 'primary_cnae', 'ai_request_count', 'ai_request_quota')
    list_filter = ('primary_cnae__default_anexo',)
    search_fields = ('company__name',)
