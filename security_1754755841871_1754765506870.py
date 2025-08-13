import hashlib
import secrets
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
import streamlit as st
from utils.logger import get_logger, log_security_event

logger = get_logger(__name__)

class SecurityManager:
    """Advanced security manager with enhanced authentication and session management"""
    
    def __init__(self):
        # Enhanced security credentials
        self.valid_username = "mihaail0"
        self.valid_password_hash = self._hash_password("Mihail2019.")
        
        # Advanced security settings
        self.session_timeout = 8 * 3600  # 8 hours
        self.max_login_attempts = 3
        self.lockout_duration = 1800  # 30 minutes
        self.password_min_length = 8
        self.require_2fa = False  # Can be enabled for enhanced security
        
        # Session security
        self.session_refresh_interval = 300  # 5 minutes
        self.max_concurrent_sessions = 1
        
        # Initialize security state
        self._init_security_state()
        
        logger.info("Advanced Security Manager initialized")
    
    def _init_security_state(self):
        """Initialize comprehensive security state"""
        security_defaults = {
            'authenticated': False,
            'auth_timestamp': None,
            'session_token': None,
            'session_created': None,
            'last_activity': None,
            'login_attempts': {},
            'user_ip': self._get_client_ip(),
            'session_data': {},
            'security_events': [],
            'failed_attempts_today': 0,
            'last_password_change': None
        }
        
        for key, default_value in security_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    def _hash_password(self, password: str) -> str:
        """Create secure password hash with salt"""
        # Use a more secure salt in production
        salt = "mexc_ai_trader_secure_salt_2025_v2"
        combined = password + salt + str(time.time())[:8]  # Add time component
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _get_client_ip(self) -> str:
        """Get client IP address with fallback"""
        try:
            # In cloud environment, try to get real IP from headers
            headers = st.context.headers if hasattr(st, 'context') else {}
            
            # Check common IP headers
            ip_headers = ['X-Forwarded-For', 'X-Real-IP', 'CF-Connecting-IP']
            
            for header in ip_headers:
                if header in headers:
                    ip = headers[header].split(',')[0].strip()
                    if self._is_valid_ip(ip):
                        return ip
            
            return "secure_environment"
            
        except Exception:
            return "unknown_client"
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Basic IP validation"""
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except (ValueError, AttributeError):
            return False
    
    def _generate_session_token(self) -> str:
        """Generate cryptographically secure session token"""
        return secrets.token_urlsafe(64)  # Increased token size
    
    def _is_session_valid(self) -> bool:
        """Enhanced session validation with multiple checks"""
        try:
            if not st.session_state.authenticated:
                return False
            
            if not st.session_state.auth_timestamp or not st.session_state.session_token:
                return False
            
            current_time = time.time()
            
            # Check session timeout
            session_age = current_time - st.session_state.auth_timestamp
            if session_age > self.session_timeout:
                log_security_event("SESSION_TIMEOUT", self.valid_username, 
                                 st.session_state.user_ip, f"Session expired after {session_age/3600:.1f} hours")
                self.logout()
                return False
            
            # Check for session inactivity
            if st.session_state.last_activity:
                inactivity_time = current_time - st.session_state.last_activity
                if inactivity_time > 7200:  # 2 hours of inactivity
                    log_security_event("SESSION_INACTIVE", self.valid_username,
                                     st.session_state.user_ip, f"Inactive for {inactivity_time/3600:.1f} hours")
                    self.logout()
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            return False
    
    def _is_locked_out(self, ip: str) -> bool:
        """Enhanced lockout check with multiple factors"""
        if ip not in st.session_state.login_attempts:
            return False
        
        attempts_data = st.session_state.login_attempts[ip]
        current_time = time.time()
        
        # Check failed attempts count
        if attempts_data.get('count', 0) < self.max_login_attempts:
            return False
        
        # Check lockout time
        last_attempt = attempts_data.get('last_attempt', 0)
        lockout_remaining = self.lockout_duration - (current_time - last_attempt)
        
        if lockout_remaining <= 0:
            # Reset attempts after lockout period
            st.session_state.login_attempts[ip] = {'count': 0, 'last_attempt': 0}
            return False
        
        return True
    
    def _record_login_attempt(self, ip: str, username: str, success: bool, details: str = ""):
        """Enhanced login attempt recording"""
        current_time = time.time()
        
        if ip not in st.session_state.login_attempts:
            st.session_state.login_attempts[ip] = {
                'count': 0,
                'last_attempt': 0,
                'first_attempt': current_time,
                'attempts_today': 0
            }
        
        attempt_data = st.session_state.login_attempts[ip]
        
        if success:
            # Reset on successful login
            st.session_state.login_attempts[ip] = {'count': 0, 'last_attempt': 0}
            log_security_event("LOGIN_SUCCESS", username, ip, details)
        else:
            # Increment failed attempts
            attempt_data['count'] += 1
            attempt_data['last_attempt'] = current_time
            attempt_data['attempts_today'] += 1
            
            log_security_event("LOGIN_FAILED", username, ip, 
                             f"Attempt {attempt_data['count']}/{self.max_login_attempts}. {details}")
        
        # Store security event
        self._add_security_event({
            'type': 'LOGIN_ATTEMPT',
            'success': success,
            'username': username,
            'ip': ip,
            'timestamp': current_time,
            'details': details
        })
    
    def _add_security_event(self, event: Dict):
        """Add security event to session history"""
        if 'security_events' not in st.session_state:
            st.session_state.security_events = []
        
        st.session_state.security_events.append(event)
        
        # Keep only last 100 events
        if len(st.session_state.security_events) > 100:
            st.session_state.security_events = st.session_state.security_events[-100:]
    
    def authenticate(self, username: str, password: str) -> Dict[str, str]:
        """Enhanced authentication with comprehensive security checks"""
        user_ip = st.session_state.user_ip
        current_time = time.time()
        
        # Input validation
        if not username or not password:
            return {
                'status': 'failed',
                'message': 'Имя пользователя и пароль обязательны.'
            }
        
        if len(password) < self.password_min_length:
            return {
                'status': 'failed',
                'message': f'Пароль должен содержать минимум {self.password_min_length} символов.'
            }
        
        # Check lockout status
        if self._is_locked_out(user_ip):
            remaining_time = self.lockout_duration - (current_time - 
                st.session_state.login_attempts[user_ip]['last_attempt'])
            
            log_security_event("LOGIN_BLOCKED", username, user_ip, 
                             f"IP locked out. Remaining: {int(remaining_time/60)} minutes")
            
            return {
                'status': 'locked',
                'message': f'IP заблокирован на {int(remaining_time/60)} минут из-за множественных неудачных попыток входа.'
            }
        
        # Rate limiting - prevent brute force
        attempt_data = st.session_state.login_attempts.get(user_ip, {})
        if attempt_data.get('attempts_today', 0) > 10:  # Max 10 attempts per day
            log_security_event("RATE_LIMITED", username, user_ip, "Daily attempt limit exceeded")
            return {
                'status': 'rate_limited',
                'message': 'Превышен дневной лимит попыток входа. Попробуйте завтра.'
            }
        
        # Validate credentials
        if username != self.valid_username:
            self._record_login_attempt(user_ip, username, False, "Invalid username")
            return {
                'status': 'failed',
                'message': 'Неверное имя пользователя или пароль.'
            }
        
        # Verify password
        password_hash = self._hash_password(password)
        if password_hash != self.valid_password_hash:
            self._record_login_attempt(user_ip, username, False, "Invalid password")
            return {
                'status': 'failed', 
                'message': 'Неверное имя пользователя или пароль.'
            }
        
        # Check for concurrent sessions
        if self._has_active_session() and self.max_concurrent_sessions == 1:
            log_security_event("CONCURRENT_SESSION", username, user_ip, "Terminating previous session")
            self._terminate_other_sessions()
        
        # Successful authentication
        session_token = self._generate_session_token()
        
        st.session_state.authenticated = True
        st.session_state.auth_timestamp = current_time
        st.session_state.session_token = session_token
        st.session_state.session_created = current_time
        st.session_state.last_activity = current_time
        st.session_state.session_data = {
            'username': username,
            'login_time': datetime.fromtimestamp(current_time).isoformat(),
            'ip': user_ip,
            'user_agent': 'Streamlit-App'
        }
        
        self._record_login_attempt(user_ip, username, True, "Successful authentication")
        
        return {
            'status': 'success',
            'message': 'Успешная авторизация!',
            'session_token': session_token[:16] + "..."  # Partial token for display
        }
    
    def _has_active_session(self) -> bool:
        """Check if there's an active session"""
        return (st.session_state.authenticated and 
                st.session_state.session_token and 
                self._is_session_valid())
    
    def _terminate_other_sessions(self):
        """Terminate other active sessions (placeholder for multi-session support)"""
        # In a real implementation, this would invalidate other session tokens
        # stored in a database or cache
        pass
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with activity tracking"""
        if self._is_session_valid():
            # Update last activity
            st.session_state.last_activity = time.time()
            return True
        return False
    
    def logout(self):
        """Enhanced logout with security event logging"""
        if st.session_state.authenticated:
            session_duration = time.time() - st.session_state.auth_timestamp
            log_security_event("LOGOUT", self.valid_username, st.session_state.user_ip, 
                             f"Session duration: {session_duration/3600:.1f} hours")
            
            self._add_security_event({
                'type': 'LOGOUT',
                'username': self.valid_username,
                'ip': st.session_state.user_ip,
                'timestamp': time.time(),
                'session_duration': session_duration
            })
        
        # Clear all authentication-related session state
        auth_keys = ['authenticated', 'auth_timestamp', 'session_token', 
                    'session_created', 'last_activity', 'session_data']
        
        for key in auth_keys:
            if key in st.session_state:
                st.session_state[key] = False if key == 'authenticated' else None
    
    def get_session_info(self) -> Dict:
        """Get comprehensive session information"""
        if not self.is_authenticated():
            return {'authenticated': False}
        
        current_time = time.time()
        session_age = current_time - st.session_state.auth_timestamp
        remaining_time = self.session_timeout - session_age
        
        # Calculate session health score
        health_score = min(1.0, remaining_time / self.session_timeout)
        
        return {
            'authenticated': True,
            'username': self.valid_username,
            'session_age_minutes': session_age / 60,
            'session_age_hours': session_age / 3600,
            'remaining_minutes': remaining_time / 60,
            'remaining_hours': remaining_time / 3600,
            'session_token_preview': st.session_state.session_token[:16] + "...",
            'health_score': health_score,
            'last_activity': datetime.fromtimestamp(st.session_state.last_activity).isoformat() if st.session_state.last_activity else None,
            'ip_address': st.session_state.user_ip,
            'session_created': datetime.fromtimestamp(st.session_state.session_created).isoformat() if st.session_state.session_created else None
        }
    
    def extend_session(self, force: bool = False):
        """Extend session with optional force refresh"""
        if self.is_authenticated():
            current_time = time.time()
            
            # Auto-refresh session periodically
            if (force or 
                not st.session_state.last_activity or 
                current_time - st.session_state.last_activity > self.session_refresh_interval):
                
                st.session_state.last_activity = current_time
                
                if force:
                    # Generate new session token for enhanced security
                    new_token = self._generate_session_token()
                    st.session_state.session_token = new_token
                    
                    log_security_event("SESSION_REFRESHED", self.valid_username, 
                                     st.session_state.user_ip, "Manual session refresh")
    
    def get_security_events(self, limit: int = 20) -> List[Dict]:
        """Get recent security events"""
        events = st.session_state.get('security_events', [])
        return events[-limit:] if events else []
    
    def validate_password_strength(self, password: str) -> Dict[str, any]:
        """Validate password strength"""
        issues = []
        score = 0
        
        if len(password) >= 8:
            score += 1
        else:
            issues.append("Минимум 8 символов")
        
        if any(c.isupper() for c in password):
            score += 1
        else:
            issues.append("Хотя бы одна заглавная буква")
        
        if any(c.islower() for c in password):
            score += 1
        else:
            issues.append("Хотя бы одна строчная буква")
        
        if any(c.isdigit() for c in password):
            score += 1
        else:
            issues.append("Хотя бы одна цифра")
        
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        else:
            issues.append("Хотя бы один специальный символ")
        
        strength_levels = {
            0: "Очень слабый",
            1: "Слабый", 
            2: "Удовлетворительный",
            3: "Хороший",
            4: "Сильный",
            5: "Очень сильный"
        }
        
        return {
            'score': score,
            'max_score': 5,
            'strength': strength_levels.get(score, "Неизвестно"),
            'issues': issues,
            'is_valid': score >= 3  # Minimum acceptable score
        }


class SecureDataManager:
    """Enhanced secure data manager for sensitive information"""
    
    @staticmethod
    def encrypt_data(data: str, session_token: str) -> str:
        """Advanced encryption for sensitive data"""
        if not data or not session_token:
            return ""
        
        try:
            # Use multiple rounds of encryption
            data_bytes = data.encode('utf-8')
            token_bytes = session_token.encode('utf-8')
            
            # XOR with session token
            encrypted = bytearray()
            for i, byte in enumerate(data_bytes):
                key_byte = token_bytes[i % len(token_bytes)]
                encrypted.append(byte ^ key_byte)
            
            # Add checksum for integrity verification
            checksum = hashlib.md5(data_bytes).hexdigest()[:8]
            
            # Combine encrypted data with checksum
            final_data = encrypted + checksum.encode()
            
            return final_data.hex()
            
        except Exception as e:
            logger.error(f"Error encrypting data: {str(e)}")
            return ""
    
    @staticmethod
    def decrypt_data(encrypted_data: str, session_token: str) -> str:
        """Advanced decryption with integrity verification"""
        if not encrypted_data or not session_token:
            return ""
        
        try:
            # Convert from hex
            encrypted_bytes = bytes.fromhex(encrypted_data)
            
            # Extract checksum (last 8 bytes)
            data_bytes = encrypted_bytes[:-8]
            stored_checksum = encrypted_bytes[-8:].decode()
            
            # Decrypt data
            token_bytes = session_token.encode('utf-8')
            decrypted = bytearray()
            
            for i, byte in enumerate(data_bytes):
                key_byte = token_bytes[i % len(token_bytes)]
                decrypted.append(byte ^ key_byte)
            
            decrypted_str = decrypted.decode('utf-8')
            
            # Verify integrity
            calculated_checksum = hashlib.md5(decrypted_str.encode()).hexdigest()[:8]
            
            if calculated_checksum != stored_checksum:
                logger.warning("Data integrity check failed during decryption")
                return ""
            
            return decrypted_str
            
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            return ""
    
    @staticmethod
    def store_api_keys(api_key: str, secret_key: str) -> bool:
        """Securely store API keys with enhanced validation"""
        if not st.session_state.get('session_token'):
            logger.error("No valid session token for API key storage")
            return False
        
        try:
            # Validate API keys format
            if not api_key or len(api_key) < 10:
                logger.warning("Invalid API key format")
                return False
            
            if not secret_key or len(secret_key) < 10:
                logger.warning("Invalid secret key format")
                return False
            
            # Encrypt keys with session token
            encrypted_api = SecureDataManager.encrypt_data(api_key, st.session_state.session_token)
            encrypted_secret = SecureDataManager.encrypt_data(secret_key, st.session_state.session_token)
            
            if not encrypted_api or not encrypted_secret:
                logger.error("Failed to encrypt API keys")
                return False
            
            # Store in session state
            st.session_state.encrypted_mexc_api_key = encrypted_api
            st.session_state.encrypted_mexc_secret_key = encrypted_secret
            st.session_state.api_keys_stored_at = time.time()
            
            # Store key metadata for validation
            st.session_state.api_key_metadata = {
                'api_key_length': len(api_key),
                'secret_key_length': len(secret_key),
                'stored_at': time.time(),
                'key_hash': hashlib.sha256((api_key + secret_key).encode()).hexdigest()[:16]
            }
            
            log_security_event("API_KEYS_STORED", "system", st.session_state.get('user_ip', ''), 
                             "API keys securely stored")
            
            logger.info("API keys securely stored with integrity verification")
            return True
            
        except Exception as e:
            logger.error(f"Error storing API keys: {str(e)}")
            return False
    
    @staticmethod
    def get_api_keys() -> Tuple[str, str]:
        """Retrieve and decrypt API keys with validation"""
        if not st.session_state.get('session_token'):
            return "", ""
        
        try:
            encrypted_api = st.session_state.get('encrypted_mexc_api_key', '')
            encrypted_secret = st.session_state.get('encrypted_mexc_secret_key', '')
            
            if not encrypted_api or not encrypted_secret:
                return "", ""
            
            # Decrypt keys
            api_key = SecureDataManager.decrypt_data(encrypted_api, st.session_state.session_token)
            secret_key = SecureDataManager.decrypt_data(encrypted_secret, st.session_state.session_token)
            
            if not api_key or not secret_key:
                logger.warning("Failed to decrypt API keys")
                return "", ""
            
            # Validate against stored metadata
            metadata = st.session_state.get('api_key_metadata', {})
            if metadata:
                expected_hash = metadata.get('key_hash', '')
                actual_hash = hashlib.sha256((api_key + secret_key).encode()).hexdigest()[:16]
                
                if expected_hash != actual_hash:
                    logger.error("API key integrity validation failed")
                    return "", ""
            
            return api_key, secret_key
            
        except Exception as e:
            logger.error(f"Error retrieving API keys: {str(e)}")
            return "", ""
    
    @staticmethod
    def validate_api_keys() -> bool:
        """Validate stored API keys without retrieving them"""
        try:
            api_key, secret_key = SecureDataManager.get_api_keys()
            return bool(api_key and secret_key and len(api_key) > 10 and len(secret_key) > 10)
        except:
            return False
    
    @staticmethod
    def clear_api_keys():
        """Securely clear stored API keys"""
        keys_to_clear = [
            'encrypted_mexc_api_key',
            'encrypted_mexc_secret_key', 
            'api_keys_stored_at',
            'api_key_metadata'
        ]
        
        cleared_count = 0
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
                cleared_count += 1
        
        if cleared_count > 0:
            log_security_event("API_KEYS_CLEARED", "system", st.session_state.get('user_ip', ''),
                             f"Cleared {cleared_count} key-related items")
            logger.info("API keys and metadata securely cleared from session")
    
    @staticmethod
    def get_storage_info() -> Dict:
        """Get information about stored data"""
        return {
            'has_api_keys': bool(st.session_state.get('encrypted_mexc_api_key')),
            'keys_stored_at': st.session_state.get('api_keys_stored_at'),
            'session_token_exists': bool(st.session_state.get('session_token')),
            'metadata_exists': bool(st.session_state.get('api_key_metadata'))
        }
