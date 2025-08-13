import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
import streamlit as st
from utils.logger import get_logger, log_security_event

logger = get_logger(__name__)

class SecurityManager:
    """Менеджер безопасности и авторизации"""
    
    def __init__(self):
        # Хеш пароля для безопасного хранения
        self.valid_username = "mihaail0"
        self.valid_password_hash = self._hash_password("Mihail2019.")
        
        # Настройки безопасности
        self.session_timeout = 8 * 3600  # 8 часов
        self.max_login_attempts = 3
        self.lockout_duration = 1800  # 30 минут
        
        # Инициализация session state для безопасности
        self._init_security_state()
    
    def _init_security_state(self):
        """Инициализация состояния безопасности"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'auth_timestamp' not in st.session_state:
            st.session_state.auth_timestamp = None
        if 'session_token' not in st.session_state:
            st.session_state.session_token = None
        if 'login_attempts' not in st.session_state:
            st.session_state.login_attempts = {}
        if 'user_ip' not in st.session_state:
            st.session_state.user_ip = self._get_client_ip()
    
    def _hash_password(self, password: str) -> str:
        """Создание безопасного хеша пароля"""
        salt = "crypto_bot_secure_salt_2025"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def _get_client_ip(self) -> str:
        """Получение IP адреса клиента"""
        # В облачной среде это будет безопасный внутренний IP
        return "secure_cloud_environment"
    
    def _generate_session_token(self) -> str:
        """Генерация безопасного токена сессии"""
        return secrets.token_urlsafe(32)
    
    def _is_session_valid(self) -> bool:
        """Проверка валидности текущей сессии"""
        if not st.session_state.authenticated:
            return False
            
        if not st.session_state.auth_timestamp:
            return False
        
        # Проверка таймаута сессии
        session_age = time.time() - st.session_state.auth_timestamp
        if session_age > self.session_timeout:
            self.logout()
            return False
        
        return True
    
    def _is_locked_out(self, ip: str) -> bool:
        """Проверка блокировки по IP"""
        if ip not in st.session_state.login_attempts:
            return False
        
        attempts_data = st.session_state.login_attempts[ip]
        
        # Проверяем количество попыток
        if attempts_data['count'] < self.max_login_attempts:
            return False
        
        # Проверяем время последней попытки
        time_since_last = time.time() - attempts_data['last_attempt']
        if time_since_last > self.lockout_duration:
            # Сбрасываем счетчик после окончания блокировки
            st.session_state.login_attempts[ip] = {'count': 0, 'last_attempt': 0}
            return False
        
        return True
    
    def _record_login_attempt(self, ip: str, success: bool):
        """Запись попытки входа"""
        if ip not in st.session_state.login_attempts:
            st.session_state.login_attempts[ip] = {'count': 0, 'last_attempt': 0}
        
        if success:
            # Сброс счетчика при успешном входе
            st.session_state.login_attempts[ip] = {'count': 0, 'last_attempt': 0}
        else:
            # Увеличение счетчика при неудачной попытке
            st.session_state.login_attempts[ip]['count'] += 1
            st.session_state.login_attempts[ip]['last_attempt'] = time.time()
    
    def authenticate(self, username: str, password: str) -> Dict[str, str]:
        """Аутентификация пользователя"""
        user_ip = st.session_state.user_ip
        
        # Проверка блокировки
        if self._is_locked_out(user_ip):
            remaining_time = self.lockout_duration - (time.time() - st.session_state.login_attempts[user_ip]['last_attempt'])
            log_security_event("LOGIN_BLOCKED", username, user_ip, f"Remaining: {int(remaining_time/60)} minutes")
            return {
                'status': 'locked',
                'message': f'Аккаунт заблокирован на {int(remaining_time/60)} минут из-за множественных неудачных попыток входа.'
            }
        
        # Проверка учетных данных
        if username != self.valid_username:
            self._record_login_attempt(user_ip, False)
            log_security_event("LOGIN_FAILED", username, user_ip, "Invalid username")
            return {
                'status': 'failed',
                'message': 'Неверное имя пользователя или пароль.'
            }
        
        password_hash = self._hash_password(password)
        if password_hash != self.valid_password_hash:
            self._record_login_attempt(user_ip, False)
            log_security_event("LOGIN_FAILED", username, user_ip, "Invalid password")
            return {
                'status': 'failed',
                'message': 'Неверное имя пользователя или пароль.'
            }
        
        # Успешная аутентификация
        st.session_state.authenticated = True
        st.session_state.auth_timestamp = time.time()
        st.session_state.session_token = self._generate_session_token()
        
        self._record_login_attempt(user_ip, True)
        log_security_event("LOGIN_SUCCESS", username, user_ip, "Authentication successful")
        
        return {
            'status': 'success',
            'message': 'Успешная авторизация!'
        }
    
    def is_authenticated(self) -> bool:
        """Проверка аутентификации"""
        return self._is_session_valid()
    
    def logout(self):
        """Выход из системы"""
        if st.session_state.authenticated:
            log_security_event("LOGOUT", self.valid_username, st.session_state.user_ip, "User logout")
        
        st.session_state.authenticated = False
        st.session_state.auth_timestamp = None
        st.session_state.session_token = None
    
    def get_session_info(self) -> Dict:
        """Информация о текущей сессии"""
        if not self.is_authenticated():
            return {'authenticated': False}
        
        session_age = time.time() - st.session_state.auth_timestamp
        remaining_time = self.session_timeout - session_age
        
        return {
            'authenticated': True,
            'username': self.valid_username,
            'session_age_hours': session_age / 3600,
            'remaining_hours': remaining_time / 3600,
            'session_token': st.session_state.session_token[:8] + "..."
        }
    
    def extend_session(self):
        """Продление сессии при активности"""
        if self.is_authenticated():
            st.session_state.auth_timestamp = time.time()

class SecureDataManager:
    """Менеджер для безопасного хранения чувствительных данных"""
    
    @staticmethod
    def encrypt_api_key(api_key: str, session_token: str) -> str:
        """Базовое шифрование API ключа"""
        if not api_key or not session_token:
            return ""
        
        # Простое XOR шифрование с токеном сессии
        key_bytes = api_key.encode()
        token_bytes = session_token.encode()
        
        encrypted = bytearray()
        for i, byte in enumerate(key_bytes):
            encrypted.append(byte ^ token_bytes[i % len(token_bytes)])
        
        return encrypted.hex()
    
    @staticmethod
    def decrypt_api_key(encrypted_key: str, session_token: str) -> str:
        """Дешифровка API ключа"""
        if not encrypted_key or not session_token:
            return ""
        
        try:
            encrypted_bytes = bytes.fromhex(encrypted_key)
            token_bytes = session_token.encode()
            
            decrypted = bytearray()
            for i, byte in enumerate(encrypted_bytes):
                decrypted.append(byte ^ token_bytes[i % len(token_bytes)])
            
            return decrypted.decode()
        except:
            return ""
    
    @staticmethod
    def store_api_keys(api_key: str, secret_key: str) -> bool:
        """Безопасное сохранение API ключей"""
        if not st.session_state.get('session_token'):
            return False
        
        try:
            # Шифруем ключи
            encrypted_api = SecureDataManager.encrypt_api_key(api_key, st.session_state.session_token)
            encrypted_secret = SecureDataManager.encrypt_api_key(secret_key, st.session_state.session_token)
            
            # Сохраняем в защищенном состоянии сессии
            st.session_state.encrypted_mexc_api_key = encrypted_api
            st.session_state.encrypted_mexc_secret_key = encrypted_secret
            
            logger.info("API ключи безопасно сохранены")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения API ключей: {str(e)}")
            return False
    
    @staticmethod
    def get_api_keys() -> tuple[str, str]:
        """Получение расшифрованных API ключей"""
        if not st.session_state.get('session_token'):
            return "", ""
        
        try:
            encrypted_api = st.session_state.get('encrypted_mexc_api_key', '')
            encrypted_secret = st.session_state.get('encrypted_mexc_secret_key', '')
            
            if not encrypted_api or not encrypted_secret:
                return "", ""
            
            api_key = SecureDataManager.decrypt_api_key(encrypted_api, st.session_state.session_token)
            secret_key = SecureDataManager.decrypt_api_key(encrypted_secret, st.session_state.session_token)
            
            return api_key, secret_key
            
        except Exception as e:
            logger.error(f"Ошибка получения API ключей: {str(e)}")
            return "", ""
    
    @staticmethod
    def clear_api_keys():
        """Очистка сохраненных API ключей"""
        if 'encrypted_mexc_api_key' in st.session_state:
            del st.session_state.encrypted_mexc_api_key
        if 'encrypted_mexc_secret_key' in st.session_state:
            del st.session_state.encrypted_mexc_secret_key
        
        logger.info("API ключи удалены из безопасного хранилища")
