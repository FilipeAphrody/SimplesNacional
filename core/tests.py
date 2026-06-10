from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Company, CompanyUser

User = get_user_model()

class OnboardingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")

    def test_onboarding_creates_company(self):
        response = self.client.post(reverse('onboarding'), {
            'cnpj': '12.345.678/0001-99',
            'name': 'Test Company LLC'
        })
        self.assertEqual(response.status_code, 302) # Redirects to dashboard
        self.assertTrue(Company.objects.filter(cnpj='12.345.678/0001-99').exists())
        self.assertEqual(self.user.companies.count(), 1)
        self.assertEqual(self.user.companies.first().role, 'OWNER')

class SuperadminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.normal_user = User.objects.create_user(username="normal", password="pwd")
        self.super_user = User.objects.create_superuser(username="admin", password="pwd")

    def test_normal_user_rejected(self):
        self.client.login(username="normal", password="pwd")
        response = self.client.get(reverse('superadmin'))
        self.assertEqual(response.status_code, 302) # Redirects to login

    def test_superuser_accepted(self):
        self.client.login(username="admin", password="pwd")
        response = self.client.get(reverse('superadmin'))
        self.assertEqual(response.status_code, 200)
