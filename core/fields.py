from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken
import base64

def get_fernet():
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
    if not key:
        raise ValueError("FIELD_ENCRYPTION_KEY is missing from settings")
    return Fernet(key.encode('utf-8'))

class EncryptedCharField(models.CharField):
    """
    A custom CharField that seamlessly encrypts data on save and decrypts it on read
    using the cryptography Fernet symmetric encryption.
    """
    def __init__(self, *args, **kwargs):
        # We need a longer max_length in the database because ciphertext is longer than plaintext
        if 'max_length' in kwargs:
            kwargs['max_length'] = max(255, kwargs['max_length'] * 4)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == '':
            return value
        
        fernet = get_fernet()
        ciphertext = fernet.encrypt(str(value).encode('utf-8'))
        return ciphertext.decode('utf-8')

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
            
        fernet = get_fernet()
        try:
            plaintext = fernet.decrypt(value.encode('utf-8'))
            return plaintext.decode('utf-8')
        except (InvalidToken, TypeError, ValueError):
            # If decryption fails (e.g., legacy plaintext data in db before encryption was added), return as is
            # In a real environment, you'd migrate the data properly first.
            return value

    def to_python(self, value):
        # This handles form serialization
        if value is None or value == '':
            return value
        
        # If it's already an encrypted string (e.g., during model validation), try decrypting
        fernet = get_fernet()
        try:
            plaintext = fernet.decrypt(value.encode('utf-8'))
            return plaintext.decode('utf-8')
        except (InvalidToken, TypeError, ValueError):
            return value
