from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('reforma-simulator/', views.reforma_simulator_view, name='reforma_simulator'),
]
