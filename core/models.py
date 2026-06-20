from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .fields import EncryptedCharField

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

class User(AbstractUser):
    # Additional fields can be added here
    phone_number = EncryptedCharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.username

class Company(SoftDeleteModel):
    name = models.CharField(max_length=255)
    cnpj = EncryptedCharField(max_length=14, unique=True)
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

class SystemErrorLog(models.Model):
    STATUS_CHOICES = (
        ('UNRESOLVED', 'Unresolved'),
        ('RESOLVED', 'Resolved'),
    )
    message = models.TextField()
    traceback = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNRESOLVED')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"[{self.status}] {self.message[:50]}"
