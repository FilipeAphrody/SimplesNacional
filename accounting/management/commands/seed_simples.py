from django.core.management.base import BaseCommand
from decimal import Decimal
from accounting.models import TaxBracket
from core.models import User, Company, CompanyUser
from companies.models import CNAE, CompanyProfile

class Command(BaseCommand):
    help = 'Seeds the database with Simples Nacional Anexos and creates a test user.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding Simples Nacional Anexo III...')
        
        # Anexo III Data (Services)
        anexo3_data = [
            {'faixa': 1, 'min': '0.00', 'max': '180000.00', 'aliq': '0.0600', 'deduzir': '0.00'},
            {'faixa': 2, 'min': '180000.01', 'max': '360000.00', 'aliq': '0.1120', 'deduzir': '9360.00'},
            {'faixa': 3, 'min': '360000.01', 'max': '720000.00', 'aliq': '0.1350', 'deduzir': '17640.00'},
            {'faixa': 4, 'min': '720000.01', 'max': '1800000.00', 'aliq': '0.1600', 'deduzir': '35640.00'},
            {'faixa': 5, 'min': '1800000.01', 'max': '3600000.00', 'aliq': '0.2100', 'deduzir': '125640.00'},
            {'faixa': 6, 'min': '3600000.01', 'max': '4800000.00', 'aliq': '0.3300', 'deduzir': '648000.00'},
        ]

        for data in anexo3_data:
            TaxBracket.objects.update_or_create(
                anexo='III',
                faixa=data['faixa'],
                defaults={
                    'min_revenue': Decimal(data['min']),
                    'max_revenue': Decimal(data['max']),
                    'aliquota_nominal': Decimal(data['aliq']),
                    'parcela_deduzir': Decimal(data['deduzir']),
                }
            )
            
        self.stdout.write(self.style.SUCCESS('Successfully seeded Tax Brackets.'))
        
        # Create a test user and company
        user, created = User.objects.get_or_create(username='admin')
        if created:
            user.set_password('admin123')
            user.is_superuser = True
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS('Created test user "admin" with password "admin123".'))
            
        company, created = Company.objects.get_or_create(
            cnpj='12345678000199',
            defaults={'name': 'Tech Solutions Ltda'}
        )
        if created:
            CompanyUser.objects.create(user=user, company=company, role='OWNER')
            
            cnae, _ = CNAE.objects.get_or_create(
                code='6201-5/01',
                defaults={
                    'description': 'Desenvolvimento de programas de computador sob encomenda',
                    'is_subject_to_fator_r': True,
                    'default_anexo': 'III'
                }
            )
            
            CompanyProfile.objects.create(company=company, primary_cnae=cnae)
            self.stdout.write(self.style.SUCCESS('Created test company "Tech Solutions Ltda".'))
            
