import hashlib
import os
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets

from utils.logger import get_logger, log_error

logger = get_logger(__name__)

class SecurityManager:
    """Система безопасности и управления пользователями"""
    
    def __init__(self, users_file: str = "users.json", keys_file: str = "api_keys.enc"):
        self.users_file = users_file
        self.keys_file = keys_file
        self.master_key = None
        self.session_tokens = {}
        
        # Инициализация файлов
        self._init_security_files()
        
        logger.info("Security Manager initialized")
    
    def _init_security_files(self):
        """Инициализация файлов безопасности"""
        try:
            # Создаем файл пользователей если его нет
            if not os.path.exists(self.users_file):
                default_users = {
                    "admin": {
                        "password_hash": self._hash_password("admin123"),
                        "role": "admin",
                        "created_at": datetime.now().isoformat(),
                        "last_login": None,
                        "login_attempts": 0,
                        "locked_until": None
                    },
                    "trader": {
                        "password_hash": self._hash_password("trader123"),
                        "role": "trader",
                        "created_at": datetime.now().isoformat(),
                        "last_login": None,
                        "login_attempts": 0,
                        "locked_until": None
                    },
                    "mihaail0": {
                        "password_hash": self._hash_password("Mihail2019."),
                        "role": "admin",
                        "created_at": datetime.now().isoformat(),
                        "last_login": None,
                        "login_attempts": 0,
                        "locked_until": None
                    }
                }
                
                with open(self.users_file, 'w') as f:
                    json.dump(default_users, f, indent=2)
                
                logger.info("Default users file created")
            
            # Генерируем мастер-ключ для шифрования API ключей
            self._generate_master_key()
            
        except Exception as e:
            log_error("SecurityManager", e, "_init_security_files")
    
    def _generate_master_key(self):
        """Генерация мастер-ключа для шифрования"""
        try:
            # Попытка загрузить существующий ключ
            key_file = "master.key"
            
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    self.master_key = f.read()
            else:
                # Генерируем новый ключ
                password = os.getenv('MASTER_PASSWORD', 'cryptobot_master_key_2024').encode()
                salt = os.urandom(16)
                
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                
                key = base64.urlsafe_b64encode(kdf.derive(password))
                self.master_key = key
                
                # Сохраняем соль и ключ
                with open(key_file, 'wb') as f:
                    f.write(salt + key)
                
                logger.info("Master key generated and saved")
                
        except Exception as e:
            log_error("SecurityManager", e, "_generate_master_key")
            # Fallback ключ
            self.master_key = Fernet.generate_key()
    
    def _hash_password(self, password: str) -> str:
        """Хеширование пароля"""
        try:
            # Добавляем соль
            salt = secrets.token_hex(16)
            password_bytes = (password + salt).encode('utf-8')
            
            # Хешируем с SHA-256
            hash_obj = hashlib.sha256(password_bytes)
            password_hash = hash_obj.hexdigest()
            
            # Возвращаем соль + хеш
            return f"{salt}:{password_hash}"
            
        except Exception as e:
            log_error("SecurityManager", e, "_hash_password")
            return ""
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Проверка пароля"""
        try:
            if ':' not in stored_hash:
                return False
            
            salt, hash_value = stored_hash.split(':', 1)
            password_bytes = (password + salt).encode('utf-8')
            
            hash_obj = hashlib.sha256(password_bytes)
            calculated_hash = hash_obj.hexdigest()
            
            return calculated_hash == hash_value
            
        except Exception as e:
            log_error("SecurityManager", e, "_verify_password")
            return False
    
    def authenticate(self, username: str, password: str) -> bool:
        """Аутентификация пользователя"""
        try:
            if not os.path.exists(self.users_file):
                return False
            
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            
            if username not in users:
                logger.warning(f"Authentication failed: user {username} not found")
                return False
            
            user = users[username]
            
            # Проверяем блокировку аккаунта
            if user.get('locked_until'):
                locked_until = datetime.fromisoformat(user['locked_until'])
                if datetime.now() < locked_until:
                    logger.warning(f"Account {username} is locked until {locked_until}")
                    return False
                else:
                    # Разблокируем аккаунт
                    user['locked_until'] = None
                    user['login_attempts'] = 0
            
            # Проверяем пароль
            if self._verify_password(password, user['password_hash']):
                # Успешная аутентификация
                user['last_login'] = datetime.now().isoformat()
                user['login_attempts'] = 0
                user['locked_until'] = None
                
                # Создаем сессионный токен
                session_token = self._generate_session_token(username)
                self.session_tokens[session_token] = {
                    'username': username,
                    'role': user['role'],
                    'created_at': datetime.now(),
                    'expires_at': datetime.now() + timedelta(hours=24)
                }
                
                # Сохраняем изменения
                with open(self.users_file, 'w') as f:
                    json.dump(users, f, indent=2)
                
                logger.info(f"User {username} authenticated successfully")
                return True
                
            else:
                # Неудачная попытка входа
                user['login_attempts'] = user.get('login_attempts', 0) + 1
                
                # Блокируем после 5 неудачных попыток
                if user['login_attempts'] >= 5:
                    user['locked_until'] = (datetime.now() + timedelta(minutes=30)).isoformat()
                    logger.warning(f"Account {username} locked due to multiple failed attempts")
                
                # Сохраняем изменения
                with open(self.users_file, 'w') as f:
                    json.dump(users, f, indent=2)
                
                logger.warning(f"Authentication failed for user {username}")
                return False
                
        except Exception as e:
            log_error("SecurityManager", e, "authenticate")
            return False
    
    def _generate_session_token(self, username: str) -> str:
        """Генерация сессионного токена"""
        try:
            timestamp = str(int(datetime.now().timestamp()))
            random_part = secrets.token_hex(16)
            token_data = f"{username}:{timestamp}:{random_part}"
            
            # Хешируем токен
            token_hash = hashlib.sha256(token_data.encode()).hexdigest()
            return token_hash
            
        except Exception as e:
            log_error("SecurityManager", e, "_generate_session_token")
            return secrets.token_hex(32)
    
    def validate_session(self, session_token: str) -> Optional[Dict]:
        """Проверка действительности сессионного токена"""
        try:
            if session_token not in self.session_tokens:
                return None
            
            session = self.session_tokens[session_token]
            
            # Проверяем срок действия
            if datetime.now() > session['expires_at']:
                del self.session_tokens[session_token]
                return None
            
            return session
            
        except Exception as e:
            log_error("SecurityManager", e, "validate_session")
            return None
    
    def logout(self, session_token: str) -> bool:
        """Выход из системы"""
        try:
            if session_token in self.session_tokens:
                username = self.session_tokens[session_token]['username']
                del self.session_tokens[session_token]
                logger.info(f"User {username} logged out")
                return True
            return False
            
        except Exception as e:
            log_error("SecurityManager", e, "logout")
            return False
    
    def encrypt_api_keys(self, api_key: str, secret_key: str) -> str:
        """Шифрование API ключей"""
        try:
            if not self.master_key:
                self._generate_master_key()
            
            fernet = Fernet(self.master_key)
            
            # Объединяем ключи
            keys_data = json.dumps({
                'api_key': api_key,
                'secret_key': secret_key,
                'encrypted_at': datetime.now().isoformat()
            })
            
            # Шифруем
            encrypted_data = fernet.encrypt(keys_data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            log_error("SecurityManager", e, "encrypt_api_keys")
            return ""
    
    def decrypt_api_keys(self, encrypted_data: str) -> Tuple[str, str]:
        """Расшифровка API ключей"""
        try:
            if not self.master_key:
                self._generate_master_key()
            
            fernet = Fernet(self.master_key)
            
            # Расшифровываем
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(encrypted_bytes)
            
            # Парсим JSON
            keys_data = json.loads(decrypted_data.decode())
            
            return keys_data['api_key'], keys_data['secret_key']
            
        except Exception as e:
            log_error("SecurityManager", e, "decrypt_api_keys")
            return "", ""
    
    def save_user_api_keys(self, username: str, api_key: str, secret_key: str) -> bool:
        """Сохранение API ключей пользователя"""
        try:
            # Шифруем ключи
            encrypted_keys = self.encrypt_api_keys(api_key, secret_key)
            
            if not encrypted_keys:
                return False
            
            # Загружаем существующие ключи
            user_keys = {}
            if os.path.exists(self.keys_file):
                try:
                    with open(self.keys_file, 'r') as f:
                        user_keys = json.load(f)
                except:
                    pass
            
            # Сохраняем ключи пользователя
            user_keys[username] = {
                'encrypted_keys': encrypted_keys,
                'saved_at': datetime.now().isoformat()
            }
            
            # Записываем в файл
            with open(self.keys_file, 'w') as f:
                json.dump(user_keys, f, indent=2)
            
            logger.info(f"API keys saved for user {username}")
            return True
            
        except Exception as e:
            log_error("SecurityManager", e, "save_user_api_keys")
            return False
    
    def load_user_api_keys(self, username: str) -> Tuple[str, str]:
        """Загрузка API ключей пользователя"""
        try:
            if not os.path.exists(self.keys_file):
                return "", ""
            
            with open(self.keys_file, 'r') as f:
                user_keys = json.load(f)
            
            if username not in user_keys:
                return "", ""
            
            encrypted_keys = user_keys[username]['encrypted_keys']
            return self.decrypt_api_keys(encrypted_keys)
            
        except Exception as e:
            log_error("SecurityManager", e, "load_user_api_keys")
            return "", ""
    
    def create_user(self, username: str, password: str, role: str = "trader") -> bool:
        """Создание нового пользователя"""
        try:
            if not os.path.exists(self.users_file):
                users = {}
            else:
                with open(self.users_file, 'r') as f:
                    users = json.load(f)
            
            if username in users:
                logger.warning(f"User {username} already exists")
                return False
            
            # Валидация пароля
            if len(password) < 6:
                logger.warning("Password too short")
                return False
            
            users[username] = {
                'password_hash': self._hash_password(password),
                'role': role,
                'created_at': datetime.now().isoformat(),
                'last_login': None,
                'login_attempts': 0,
                'locked_until': None
            }
            
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
            
            logger.info(f"User {username} created successfully")
            return True
            
        except Exception as e:
            log_error("SecurityManager", e, "create_user")
            return False
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Смена пароля пользователя"""
        try:
            if not os.path.exists(self.users_file):
                return False
            
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            
            if username not in users:
                return False
            
            user = users[username]
            
            # Проверяем старый пароль
            if not self._verify_password(old_password, user['password_hash']):
                logger.warning(f"Old password verification failed for user {username}")
                return False
            
            # Валидация нового пароля
            if len(new_password) < 6:
                logger.warning("New password too short")
                return False
            
            # Устанавливаем новый пароль
            user['password_hash'] = self._hash_password(new_password)
            user['password_changed_at'] = datetime.now().isoformat()
            
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
            
            logger.info(f"Password changed for user {username}")
            return True
            
        except Exception as e:
            log_error("SecurityManager", e, "change_password")
            return False
    
    def get_security_log(self, days: int = 7) -> List[Dict]:
        """Получение журнала безопасности"""
        try:
            # В реальном приложении здесь был бы отдельный лог
            # Сейчас возвращаем информацию о пользователях
            
            if not os.path.exists(self.users_file):
                return []
            
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            
            security_events = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for username, user_data in users.items():
                if user_data.get('last_login'):
                    last_login = datetime.fromisoformat(user_data['last_login'])
                    if last_login > cutoff_date:
                        security_events.append({
                            'timestamp': user_data['last_login'],
                            'event_type': 'login',
                            'username': username,
                            'status': 'success'
                        })
                
                if user_data.get('locked_until'):
                    locked_time = datetime.fromisoformat(user_data['locked_until'])
                    if locked_time > cutoff_date:
                        security_events.append({
                            'timestamp': user_data.get('locked_at', datetime.now().isoformat()),
                            'event_type': 'account_locked',
                            'username': username,
                            'reason': 'multiple_failed_attempts'
                        })
            
            # Сортируем по времени
            security_events.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return security_events
            
        except Exception as e:
            log_error("SecurityManager", e, "get_security_log")
            return []
    
    def validate_api_credentials(self, api_key: str, secret_key: str) -> bool:
        """Валидация API учетных данных"""
        try:
            # Базовая проверка формата
            if not api_key or not secret_key:
                return False
            
            if len(api_key) < 10 or len(secret_key) < 10:
                return False
            
            # Дополнительные проверки можно добавить здесь
            # Например, проверка с помощью тестового запроса к API
            
            return True
            
        except Exception as e:
            log_error("SecurityManager", e, "validate_api_credentials")
            return False
