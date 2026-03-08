# utils/encryption.py

from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib

class DataEncryption:
    def __init__(self):
        # Derive key from Django secret
        key = hashlib.sha256(
            settings.SECRET_KEY.encode()
        ).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key))
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# Usage for sensitive fields (e.g., student contact info)
class EncryptedCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        self.encryption = DataEncryption()
        super().__init__(*args, **kwargs)
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.encryption.decrypt(value)
    
    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encryption.encrypt(value)