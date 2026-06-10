from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    # Additional fields can be added here
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.username

class Company(models.Model):
    name = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=14, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class CompanyUser(models.Model):
    ROLE_CHOICES = (
        ('OWNER', _('Owner')),
        ('ACCOUNTANT', _('Accountant')),
        ('EMPLOYEE', _('Employee')),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='companies')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='EMPLOYEE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'company')

    def __str__(self):
        return f"{self.user.username} - {self.company.name} ({self.role})"
