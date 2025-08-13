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
        
        file_handler = logging.FileHandler('logs/mexc_ai_trader.log')
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

def log_api_call(exchange: str, endpoint: str, success: bool, response_time: float = 0, error: str = ""):
    """
    Log API calls to exchanges
    
    Args:
        exchange: Exchange name (MEXC, Binance, etc.)
        endpoint: API endpoint called
        success: Whether the call was successful
        response_time: Response time in seconds
        error: Error message if failed
    """
    logger = get_logger("API")
    
    status = "SUCCESS" if success else "FAILED"
    message = f"API Call: {exchange} | Endpoint: {endpoint} | Status: {status}"
    
    if response_time > 0:
        message += f" | Response Time: {response_time:.3f}s"
    
    if error:
        message += f" | Error: {error}"
    
    if success:
        logger.info(message)
    else:
        logger.error(message)

def log_performance_metric(metric_name: str, value: float, symbol: str = "", strategy: str = ""):
    """
    Log performance metrics
    
    Args:
        metric_name: Name of the metric (profit, loss, win_rate, etc.)
        value: Metric value
        symbol: Trading symbol (optional)
        strategy: Strategy name (optional)
    """
    logger = get_logger("PERFORMANCE")
    
    message = f"Metric: {metric_name} | Value: {value}"
    
    if symbol:
        message += f" | Symbol: {symbol}"
    if strategy:
        message += f" | Strategy: {strategy}"
    
    logger.info(message)

def log_risk_event(event: str, severity: str, details: dict = None):
    """
    Log risk management events
    
    Args:
        event: Risk event type
        severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
        details: Additional details dictionary
    """
    logger = get_logger("RISK")
    
    message = f"Risk Event: {event} | Severity: {severity}"
    
    if details:
        message += f" | Details: {details}"
    
    # Log at appropriate level based on severity
    if severity in ['HIGH', 'CRITICAL']:
        logger.error(message)
    elif severity == 'MEDIUM':
        logger.warning(message)
    else:
        logger.info(message)

