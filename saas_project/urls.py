from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from django.conf import settings
from two_factor.urls import urlpatterns as tf_urls

# Enforce 2FA strictly on the Django Admin site
from two_factor.admin import AdminSiteOTPRequired
admin.site.__class__ = AdminSiteOTPRequired

urlpatterns = [
    # Core 2FA Routes
    path('', include(tf_urls)),
    
    # Stealth Admin URL (Security through Obscurity)
    path(settings.ADMIN_URL, admin.site.urls),
    path('superadmin/', core_views.superadmin_dashboard_view, name='superadmin'),
    path('superadmin/restore-transaction/<int:tx_id>/', core_views.restore_transaction_view, name='restore_transaction'),
    path('superadmin/restore-company/<int:company_id>/', core_views.restore_company_view, name='restore_company'),
    path('superadmin/restore-category/<int:cat_id>/', core_views.restore_category_view, name='restore_category'),

    path('superadmin/export-ai-dataset/', core_views.export_ai_dataset_view, name='export_ai_dataset'),
    path('onboarding/', core_views.onboarding_view, name='onboarding'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('transactions/', include('finance.urls')),
    path('reports/', include('accounting.urls')),
    path('ai/', include('ai.urls')),
    path('', include('core.urls')),
]
