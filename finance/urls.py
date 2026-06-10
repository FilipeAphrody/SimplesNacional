from django.urls import path
from . import views

urlpatterns = [
    path('', views.transactions_view, name='transactions'),
    path('settings/', views.settings_view, name='settings'),
    path('import/', views.import_ofx_view, name='import_ofx'),
]
