from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Company, CompanyUser, SystemErrorLog

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'cnpj', 'created_at')
    search_fields = ('name', 'cnpj')

@admin.register(CompanyUser)
class CompanyUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'role')
    list_filter = ('role', 'company')
    search_fields = ('user__email', 'company__name')

@admin.register(SystemErrorLog)
class SystemErrorLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'status', 'message')
    list_filter = ('status', 'created_at')
    search_fields = ('message', 'traceback')
