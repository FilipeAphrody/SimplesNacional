from django.urls import path
from . import views

urlpatterns = [
    path('dre/', views.dre_report_view, name='dre_report'),
]
