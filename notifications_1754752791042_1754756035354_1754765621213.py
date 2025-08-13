from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
from utils.logger import get_logger

logger = get_logger(__name__)

class NotificationType(Enum):
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    SIGNAL_GENERATED = "signal_generated"
    RISK_WARNING = "risk_warning"
    SYSTEM_STATUS = "system_status"
    PERFORMANCE_UPDATE = "performance_update"

@dataclass
class Notification:
    id: str
    type: NotificationType
    title: str
    message: str
    timestamp: datetime
    read: bool = False
    data: Optional[Dict] = None
    priority: str = "normal"  # low, normal, high, critical

class NotificationManager:
    """Менеджер уведомлений для торгового бота"""
    
    def __init__(self, max_notifications: int = 100):
        self.notifications: List[Notification] = []
        self.max_notifications = max_notifications
        
    def add_notification(self, 
                        notification_type: NotificationType,
                        title: str,
                        message: str,
                        data: Optional[Dict] = None,
                        priority: str = "normal") -> str:
        """Добавить новое уведомление"""
        
        notification_id = f"{notification_type.value}_{int(datetime.now().timestamp())}"
        
        notification = Notification(
            id=notification_id,
            type=notification_type,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=priority
        )
        
        self.notifications.insert(0, notification)
        
        # Ограничиваем количество уведомлений
        if len(self.notifications) > self.max_notifications:
            self.notifications = self.notifications[:self.max_notifications]
        
        logger.info(f"Добавлено уведомление: {title}")
        return notification_id
    
    def get_notifications(self, limit: Optional[int] = None, unread_only: bool = False) -> List[Notification]:
        """Получить уведомления"""
        
        notifications = self.notifications
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        if limit:
            notifications = notifications[:limit]
        
        return notifications
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Отметить уведомление как прочитанное"""
        
        for notification in self.notifications:
            if notification.id == notification_id:
                notification.read = True
                return True
        
        return False
    
    def mark_all_as_read(self) -> int:
        """Отметить все уведомления как прочитанные"""
        
        count = 0
        for notification in self.notifications:
            if not notification.read:
                notification.read = True
                count += 1
        
        return count
    
    def get_unread_count(self) -> int:
        """Получить количество непрочитанных уведомлений"""
        return sum(1 for n in self.notifications if not n.read)
    
    def clear_old_notifications(self, days: int = 7) -> int:
        """Очистить старые уведомления"""
        
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
        
        old_count = len(self.notifications)
        self.notifications = [n for n in self.notifications if n.timestamp >= cutoff_date]
        
        removed_count = old_count - len(self.notifications)
        if removed_count > 0:
            logger.info(f"Удалено {removed_count} старых уведомлений")
        
        return removed_count
    
    def notify_trade_opened(self, symbol: str, action: str, price: float, quantity: float, confidence: float):
        """Уведомление об открытии сделки"""
        
        title = f"Открыта позиция {action} {symbol}"
        message = f"Цена: ${price:.6f}, Количество: {quantity:.4f}, Уверенность: {confidence:.1f}%"
        
        self.add_notification(
            NotificationType.TRADE_OPENED,
            title,
            message,
            data={
                "symbol": symbol,
                "action": action,
                "price": price,
                "quantity": quantity,
                "confidence": confidence
            },
            priority="high"
        )
    
    def notify_trade_closed(self, symbol: str, action: str, entry_price: float, exit_price: float, profit_pct: float):
        """Уведомление о закрытии сделки"""
        
        profit_emoji = "📈" if profit_pct > 0 else "📉"
        title = f"Закрыта позиция {action} {symbol} {profit_emoji}"
        message = f"Вход: ${entry_price:.6f}, Выход: ${exit_price:.6f}, Результат: {profit_pct:+.2f}%"
        
        self.add_notification(
            NotificationType.TRADE_CLOSED,
            title,
            message,
            data={
                "symbol": symbol,
                "action": action,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "profit_pct": profit_pct
            },
            priority="high"
        )
    
    def notify_signal_generated(self, symbol: str, action: str, confidence: float, reasoning: str):
        """Уведомление о генерации сигнала"""
        
        title = f"Сигнал {action} для {symbol}"
        message = f"Уверенность: {confidence:.1f}% - {reasoning[:100]}..."
        
        self.add_notification(
            NotificationType.SIGNAL_GENERATED,
            title,
            message,
            data={
                "symbol": symbol,
                "action": action,
                "confidence": confidence,
                "reasoning": reasoning
            }
        )
    
    def notify_risk_warning(self, message: str, risk_level: str = "medium"):
        """Уведомление о рисках"""
        
        priority_map = {"low": "normal", "medium": "high", "high": "critical"}
        priority = priority_map.get(risk_level, "normal")
        
        self.add_notification(
            NotificationType.RISK_WARNING,
            f"Предупреждение о рисках ({risk_level})",
            message,
            data={"risk_level": risk_level},
            priority=priority
        )
    
    def notify_system_status(self, status: str, message: str):
        """Уведомление о статусе системы"""
        
        priority = "high" if status in ["error", "stopped"] else "normal"
        
        self.add_notification(
            NotificationType.SYSTEM_STATUS,
            f"Статус системы: {status}",
            message,
            data={"status": status},
            priority=priority
        )
    
    def notify_performance_update(self, profit_pct: float, total_trades: int, win_rate: float):
        """Уведомление об обновлении производительности"""
        
        title = f"Обновление производительности"
        message = f"Прибыль: {profit_pct:+.2f}%, Сделки: {total_trades}, Винрейт: {win_rate:.1f}%"
        
        self.add_notification(
            NotificationType.PERFORMANCE_UPDATE,
            title,
            message,
            data={
                "profit_pct": profit_pct,
                "total_trades": total_trades,
                "win_rate": win_rate
            }
        )
    
    def to_dict(self) -> List[Dict]:
        """Конвертировать уведомления в словари для сериализации"""
        
        result = []
        for notification in self.notifications:
            notification_dict = asdict(notification)
            notification_dict['type'] = notification.type.value
            notification_dict['timestamp'] = notification.timestamp.isoformat()
            result.append(notification_dict)
        
        return result
    
    def from_dict(self, data: List[Dict]):
        """Загрузить уведомления из словарей"""
        
        self.notifications = []
        for item in data:
            try:
                notification = Notification(
                    id=item['id'],
                    type=NotificationType(item['type']),
                    title=item['title'],
                    message=item['message'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    read=item.get('read', False),
                    data=item.get('data'),
                    priority=item.get('priority', 'normal')
                )
                self.notifications.append(notification)
            except Exception as e:
                logger.error(f"Ошибка загрузки уведомления: {str(e)}")
