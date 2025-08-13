import logging
import os
from datetime import datetime
from typing import Optional

def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Создание и настройка логгера"""
    
    logger = logging.getLogger(name)
    
    # Проверяем, не настроен ли уже логгер
    if logger.handlers:
        return logger
    
    # Настройка уровня логирования
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Создание форматтера
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловый обработчик
    try:
        os.makedirs('logs', exist_ok=True)
        file_handler = logging.FileHandler(
            f'logs/cryptobot_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        # Игнорируем ошибки создания файлового логгера
        pass
    
    return logger

def log_trading_action(symbol: str, action: str, quantity: float, price: float, 
                      reason: str = "", success: bool = True) -> None:
    """Логирование торговых действий"""
    
    logger = get_logger("trading_actions")
    
    status = "SUCCESS" if success else "FAILED"
    message = f"{status} - {action} {quantity} {symbol} at ${price:.4f}"
    
    if reason:
        message += f" | Reason: {reason}"
    
    if success:
        logger.info(message)
    else:
        logger.error(message)

def log_error(component: str, error: Exception, context: str = "") -> None:
    """Логирование ошибок"""
    
    logger = get_logger("errors")
    
    message = f"ERROR in {component}: {str(error)}"
    if context:
        message += f" | Context: {context}"
    
    logger.error(message, exc_info=True)

def log_performance(metrics: dict) -> None:
    """Логирование метрик производительности"""
    
    logger = get_logger("performance")
    
    message = "Performance metrics: "
    message += " | ".join([f"{k}: {v}" for k, v in metrics.items()])
    
    logger.info(message)
