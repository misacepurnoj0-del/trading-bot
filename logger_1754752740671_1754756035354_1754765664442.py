import logging
import sys
from datetime import datetime
import os

def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Create and configure logger for the application
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set level
    logger.setLevel(getattr(logging, level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler for errors (optional, if writable directory exists)
    try:
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        file_handler = logging.FileHandler('logs/cryptobot.log')
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        # Skip file logging if directory is not writable
        pass
    
    return logger

def log_trading_action(action: str, symbol: str = "", details: dict = None):
    """
    Log trading-specific actions with structured format
    
    Args:
        action: Trading action (buy, sell, signal, etc.)
        symbol: Trading symbol
        details: Additional details dictionary
    """
    logger = get_logger("TRADING")
    
    message = f"Action: {action}"
    if symbol:
        message += f" | Symbol: {symbol}"
    if details:
        message += f" | Details: {details}"
    
    logger.info(message)

def log_security_event(event: str, user: str = "", ip: str = "", details: str = ""):
    """
    Log security-related events
    
    Args:
        event: Security event type
        user: Username (if applicable)
        ip: IP address (if applicable)
        details: Additional details
    """
    logger = get_logger("SECURITY")
    
    message = f"Security Event: {event}"
    if user:
        message += f" | User: {user}"
    if ip:
        message += f" | IP: {ip}"
    if details:
        message += f" | Details: {details}"
    
    logger.warning(message)
