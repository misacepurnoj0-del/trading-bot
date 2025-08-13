import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional
import json

from utils.logger import get_logger, log_error

logger = get_logger(__name__)

class NotificationManager:
    """Система уведомлений для торгового бота"""
    
    def __init__(self):
        self.email_enabled = False
        self.webhook_enabled = False
        self.console_enabled = True
        
        # Email settings
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER', '')
        self.email_password = os.getenv('EMAIL_PASSWORD', '')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL', '')
        
        # Webhook settings
        self.webhook_url = os.getenv('WEBHOOK_URL', '')
        
        # Notification preferences
        self.notification_settings = {
            'trade_notifications': True,
            'signal_notifications': True,
            'error_notifications': True,
            'daily_summary': True,
            'portfolio_alerts': True
        }
        
        # Initialize email if configured
        if self.email_user and self.email_password and self.recipient_email:
            self.email_enabled = True
            logger.info("Email notifications enabled")
        
        # Initialize webhook if configured
        if self.webhook_url:
            self.webhook_enabled = True
            logger.info("Webhook notifications enabled")
        
        logger.info("Notification Manager initialized")
    
    def send_trade_notification(self, symbol: str, action: str, quantity: float, 
                              price: float, confidence: float, success: bool = True) -> None:
        """Отправка уведомления о сделке"""
        try:
            status = "✅ Успешно" if success else "❌ Ошибка"
            
            message = {
                'type': 'trade',
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': price,
                'confidence': confidence,
                'success': success,
                'title': f"{status} - Сделка {action} {symbol}",
                'message': f"Символ: {symbol}\nДействие: {action}\nКоличество: {quantity}\n"
                          f"Цена: ${price:.4f}\nУверенность: {confidence:.1f}%"
            }
            
            if self.notification_settings['trade_notifications']:
                self._send_notification(message)
                
        except Exception as e:
            log_error("NotificationManager", e, "send_trade_notification")
    
    def send_signal_notification(self, symbol: str, signal_type: str, 
                               confidence: float, reasoning: str) -> None:
        """Отправка уведомления о торговом сигнале"""
        try:
            signal_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(signal_type, "⚪")
            
            message = {
                'type': 'signal',
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'signal_type': signal_type,
                'confidence': confidence,
                'reasoning': reasoning,
                'title': f"{signal_emoji} Сигнал {signal_type} для {symbol}",
                'message': f"Символ: {symbol}\nСигнал: {signal_type}\n"
                          f"Уверенность: {confidence:.1f}%\nОбоснование: {reasoning[:100]}..."
            }
            
            if self.notification_settings['signal_notifications']:
                self._send_notification(message)
                
        except Exception as e:
            log_error("NotificationManager", e, "send_signal_notification")
    
    def send_error_notification(self, error_type: str, error_message: str, 
                              component: str = "") -> None:
        """Отправка уведомления об ошибке"""
        try:
            message = {
                'type': 'error',
                'timestamp': datetime.now().isoformat(),
                'error_type': error_type,
                'error_message': error_message,
                'component': component,
                'title': f"🚨 Ошибка в системе: {error_type}",
                'message': f"Компонент: {component}\nТип ошибки: {error_type}\n"
                          f"Сообщение: {error_message}"
            }
            
            if self.notification_settings['error_notifications']:
                self._send_notification(message)
                
        except Exception as e:
            logger.error(f"Error sending error notification: {str(e)}")
    
    def send_portfolio_alert(self, alert_type: str, message: str, 
                           portfolio_data: Dict = None) -> None:
        """Отправка уведомления о состоянии портфеля"""
        try:
            alert_emoji = {
                'profit': '💰',
                'loss': '📉',
                'risk': '⚠️',
                'optimization': '🎯'
            }.get(alert_type, '📊')
            
            notification = {
                'type': 'portfolio_alert',
                'timestamp': datetime.now().isoformat(),
                'alert_type': alert_type,
                'message': message,
                'portfolio_data': portfolio_data,
                'title': f"{alert_emoji} Уведомление о портфеле: {alert_type}",
                'message': message
            }
            
            if self.notification_settings['portfolio_alerts']:
                self._send_notification(notification)
                
        except Exception as e:
            log_error("NotificationManager", e, "send_portfolio_alert")
    
    def send_daily_summary(self, summary_data: Dict) -> None:
        """Отправка ежедневной сводки"""
        try:
            total_trades = summary_data.get('total_trades', 0)
            profitable_trades = summary_data.get('profitable_trades', 0)
            total_pnl = summary_data.get('total_pnl', 0)
            win_rate = summary_data.get('win_rate', 0)
            
            summary_message = f"""
📊 ЕЖЕДНЕВНАЯ СВОДКА 📊

📈 Общая статистика:
• Всего сделок: {total_trades}
• Прибыльных сделок: {profitable_trades}
• Винрейт: {win_rate:.1f}%
• Общий P&L: ${total_pnl:.2f}

🎯 Активные позиции: {summary_data.get('active_positions', 0)}
⚡ Обработано сигналов: {summary_data.get('signals_processed', 0)}
🔍 Проанализировано символов: {summary_data.get('symbols_analyzed', 0)}

Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            message = {
                'type': 'daily_summary',
                'timestamp': datetime.now().isoformat(),
                'summary_data': summary_data,
                'title': "📊 Ежедневная сводка CryptoBot AI",
                'message': summary_message
            }
            
            if self.notification_settings['daily_summary']:
                self._send_notification(message)
                
        except Exception as e:
            log_error("NotificationManager", e, "send_daily_summary")
    
    def _send_notification(self, message: Dict) -> None:
        """Отправка уведомления через все активные каналы"""
        try:
            # Console notification (always enabled)
            if self.console_enabled:
                self._send_console_notification(message)
            
            # Email notification
            if self.email_enabled:
                self._send_email_notification(message)
            
            # Webhook notification
            if self.webhook_enabled:
                self._send_webhook_notification(message)
                
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
    
    def _send_console_notification(self, message: Dict) -> None:
        """Вывод уведомления в консоль"""
        try:
            timestamp = message.get('timestamp', datetime.now().isoformat())
            title = message.get('title', 'Уведомление')
            content = message.get('message', '')
            
            logger.info(f"NOTIFICATION [{timestamp}]: {title}")
            logger.info(f"Content: {content}")
            
        except Exception as e:
            logger.error(f"Error sending console notification: {str(e)}")
    
    def _send_email_notification(self, message: Dict) -> None:
        """Отправка email уведомления"""
        try:
            if not all([self.email_user, self.email_password, self.recipient_email]):
                return
            
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = self.recipient_email
            msg['Subject'] = message.get('title', 'CryptoBot AI Notification')
            
            # Create email body
            body = self._format_email_body(message)
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent to {self.recipient_email}")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
    
    def _send_webhook_notification(self, message: Dict) -> None:
        """Отправка webhook уведомления"""
        try:
            import requests
            
            payload = {
                'timestamp': message.get('timestamp'),
                'type': message.get('type'),
                'title': message.get('title'),
                'message': message.get('message'),
                'data': message
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info("Webhook notification sent successfully")
            else:
                logger.warning(f"Webhook notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending webhook notification: {str(e)}")
    
    def _format_email_body(self, message: Dict) -> str:
        """Форматирование тела email сообщения"""
        try:
            message_type = message.get('type', 'general')
            timestamp = message.get('timestamp', datetime.now().isoformat())
            content = message.get('message', '')
            
            if message_type == 'trade':
                template = f"""
🤖 CryptoBot AI - Торговое уведомление

⏰ Время: {timestamp}
{content}

---
Это автоматическое сообщение от CryptoBot AI.
                """.strip()
                
            elif message_type == 'signal':
                template = f"""
🤖 CryptoBot AI - Торговый сигнал

⏰ Время: {timestamp}
{content}

---
Это автоматическое сообщение от CryptoBot AI.
                """.strip()
                
            elif message_type == 'error':
                template = f"""
🤖 CryptoBot AI - Уведомление об ошибке

⏰ Время: {timestamp}
{content}

---
Требуется внимание администратора.
                """.strip()
                
            else:
                template = f"""
🤖 CryptoBot AI - Уведомление

⏰ Время: {timestamp}
{content}

---
Это автоматическое сообщение от CryptoBot AI.
                """.strip()
            
            return template
            
        except Exception as e:
            logger.error(f"Error formatting email body: {str(e)}")
            return f"Уведомление от CryptoBot AI\n\n{message.get('message', '')}"
    
    def update_settings(self, settings: Dict) -> None:
        """Обновление настроек уведомлений"""
        try:
            for key, value in settings.items():
                if key in self.notification_settings:
                    self.notification_settings[key] = value
            
            logger.info(f"Notification settings updated: {self.notification_settings}")
            
        except Exception as e:
            log_error("NotificationManager", e, "update_settings")
    
    def test_notifications(self) -> Dict:
        """Тестирование системы уведомлений"""
        try:
            results = {
                'console': False,
                'email': False,
                'webhook': False
            }
            
            test_message = {
                'type': 'test',
                'timestamp': datetime.now().isoformat(),
                'title': '🧪 Тест уведомлений CryptoBot AI',
                'message': 'Это тестовое сообщение для проверки системы уведомлений.'
            }
            
            # Test console
            try:
                self._send_console_notification(test_message)
                results['console'] = True
            except:
                pass
            
            # Test email
            if self.email_enabled:
                try:
                    self._send_email_notification(test_message)
                    results['email'] = True
                except:
                    pass
            
            # Test webhook
            if self.webhook_enabled:
                try:
                    self._send_webhook_notification(test_message)
                    results['webhook'] = True
                except:
                    pass
            
            return results
            
        except Exception as e:
            log_error("NotificationManager", e, "test_notifications")
            return {'console': False, 'email': False, 'webhook': False}
