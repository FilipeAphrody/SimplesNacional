from django.contrib import admin
from django.urls import path, include
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('superadmin/', core_views.superadmin_dashboard_view, name='superadmin'),
    path('superadmin/restore/<int:tx_id>/', core_views.restore_transaction_view, name='restore_transaction'),
    path('onboarding/', core_views.onboarding_view, name='onboarding'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('transactions/', include('finance.urls')),
    path('reports/', include('accounting.urls')),
    path('ai/', include('ai.urls')),
    path('', include('core.urls')),
]
