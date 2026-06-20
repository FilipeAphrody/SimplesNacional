from django.contrib import admin
from .models import CompanyHealthMetrics, AnonymizedDataSnapshot

@admin.register(CompanyHealthMetrics)
class CompanyHealthMetricsAdmin(admin.ModelAdmin):
    list_display = ('company', 'last_updated', 'bankruptcy_risk_score', 'runway_months')
    list_filter = ('last_updated',)
    search_fields = ('company__name',)

@admin.register(AnonymizedDataSnapshot)
class AnonymizedDataSnapshotAdmin(admin.ModelAdmin):
    list_display = ('snapshot_id', 'created_at', 'cnae_sector')
    list_filter = ('cnae_sector', 'created_at')
    search_fields = ('snapshot_id',)
