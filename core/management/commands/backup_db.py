from django.core.management.base import BaseCommand
from django.conf import settings
import shutil
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Creates a daily backup snapshot of the SQLite database'

    def handle(self, *args, **kwargs):
        db_path = settings.DATABASES['default'].get('NAME')
        if not db_path or not str(db_path).endswith('.sqlite3'):
            self.stdout.write(self.style.ERROR("This script only supports SQLite3 backups for now."))
            return
            
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"db_backup_{timestamp}.sqlite3"
        backup_filepath = os.path.join(backup_dir, backup_filename)
        
        try:
            shutil.copy2(db_path, backup_filepath)
            self.stdout.write(self.style.SUCCESS(f"Successfully backed up database to {backup_filepath}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to backup database: {str(e)}"))
