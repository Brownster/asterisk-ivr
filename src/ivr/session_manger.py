import json
import os
from cryptography.fernet import Fernet
from utils.logger import logger

class SessionManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        key = os.getenv("SESSION_KEY")
        if not key:
            raise ValueError("SESSION_KEY environment variable not set")
        self.cipher = Fernet(key)

    def save_session(self, call_id, data):
        session_key = f"session:{call_id}"
        encrypted = self.cipher.encrypt(json.dumps(data).encode())
        self.redis.setex(session_key, 3600, encrypted)

    def get_session(self, call_id):
        session_key = f"session:{call_id}"
        data = self.redis.get(session_key)
        if data:
            try:
                decrypted = self.cipher.decrypt(data)
                return json.loads(decrypted.decode())
            except Exception as e:
                logger.error(f"Error decrypting session data for {call_id}: {e}")
                return {}
        return {}
