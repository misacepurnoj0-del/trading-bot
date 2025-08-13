import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import os

from utils.logger import get_logger, log_error

logger = get_logger(__name__)

@dataclass
class Position:
    """Класс для представления торговой позиции"""
    symbol: str
    position_type: str  # 'LONG' or 'SHORT'
    entry_price: float
    current_price: float
    quantity: float
    entry_time: datetime
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    def __post_init__(self):
        self.update_pnl()
    
    def update_pnl(self):
        """Обновление нереализованной прибыли/убытка"""
        if self.position_type == 'LONG':
            self.unrealized_pnl = (self.current_price - self.entry_price) * self.quantity
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - self.current_price) * self.quantity
        
        if self.entry_price > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / (self.entry_price * self.quantity)) * 100

@dataclass
class Trade:
    """Класс для представления завершенной сделки"""
    id: int
    symbol: str
    trade_type: str  # 'BUY' or 'SELL'
    quantity: float
    price: float
    timestamp: datetime
    pnl: float = 0.0
    fee: float = 0.0
    analysis_data: Dict = None
    
    def __post_init__(self):
        if self.analysis_data is None:
            self.analysis_data = {}

class TradingHistory:
    """Система управления историей торгов и позициями"""
    
    def __init__(self, db_path: str = "trading_history.db"):
        self.db_path = db_path
        self.positions = {}  # Active positions
        self._init_database()
        logger.info(f"Trading History initialized with database: {db_path}")
    
    def _init_database(self):
        """Инициализация базы данных"""
        try:
            os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица для завершенных сделок
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        trade_type TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        pnl REAL DEFAULT 0,
                        fee REAL DEFAULT 0,
                        analysis_data TEXT
                    )
                """)
                
                # Таблица для активных позиций
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS positions (
                        symbol TEXT PRIMARY KEY,
                        position_type TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        current_price REAL NOT NULL,
                        quantity REAL NOT NULL,
                        entry_time TIMESTAMP NOT NULL,
                        unrealized_pnl REAL DEFAULT 0,
                        unrealized_pnl_pct REAL DEFAULT 0
                    )
                """)
                
                # Таблица для аналитики производительности
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        date DATE PRIMARY KEY,
                        total_trades INTEGER DEFAULT 0,
                        profitable_trades INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0,
                        win_rate REAL DEFAULT 0,
                        max_drawdown REAL DEFAULT 0,
                        sharpe_ratio REAL DEFAULT 0,
                        daily_return REAL DEFAULT 0
                    )
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            log_error("TradingHistory", e, "_init_database")
    
    def add_trade(self, symbol: str, trade_type: str, quantity: float, 
                  price: float, analysis_data: Dict = None) -> Trade:
        """Добавление новой сделки"""
        try:
            timestamp = datetime.now()
            
            # Calculate P&L if it's a closing trade
            pnl = 0.0
            if symbol in self.positions and trade_type == 'SELL':
                position = self.positions[symbol]
                pnl = (price - position.entry_price) * min(quantity, position.quantity)
                
                # Update or close position
                if quantity >= position.quantity:
                    # Close position completely
                    self._close_position(symbol)
                else:
                    # Partial close
                    position.quantity -= quantity
                    self._update_position(symbol, position)
            
            elif trade_type == 'BUY':
                # Open new position or add to existing
                if symbol in self.positions:
                    # Add to existing position (average price)
                    position = self.positions[symbol]
                    total_value = (position.entry_price * position.quantity) + (price * quantity)
                    total_quantity = position.quantity + quantity
                    position.entry_price = total_value / total_quantity
                    position.quantity = total_quantity
                    position.current_price = price
                    self._update_position(symbol, position)
                else:
                    # Create new position
                    position = Position(
                        symbol=symbol,
                        position_type='LONG',
                        entry_price=price,
                        current_price=price,
                        quantity=quantity,
                        entry_time=timestamp
                    )
                    self._add_position(symbol, position)
            
            # Calculate trading fee (0.1% default)
            fee = price * quantity * 0.001
            
            # Save trade to database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO trades (symbol, trade_type, quantity, price, timestamp, pnl, fee, analysis_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (symbol, trade_type, quantity, price, timestamp, pnl, fee, 
                      json.dumps(analysis_data) if analysis_data else None))
                
                trade_id = cursor.lastrowid
                conn.commit()
            
            trade = Trade(
                id=trade_id,
                symbol=symbol,
                trade_type=trade_type,
                quantity=quantity,
                price=price,
                timestamp=timestamp,
                pnl=pnl,
                fee=fee,
                analysis_data=analysis_data or {}
            )
            
            logger.info(f"Trade added: {trade_type} {quantity} {symbol} at ${price:.4f}")
            return trade
            
        except Exception as e:
            log_error("TradingHistory", e, "add_trade")
            return None
    
    def _add_position(self, symbol: str, position: Position):
        """Добавление новой позиции"""
        try:
            self.positions[symbol] = position
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO positions 
                    (symbol, position_type, entry_price, current_price, quantity, entry_time, unrealized_pnl, unrealized_pnl_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (position.symbol, position.position_type, position.entry_price, 
                      position.current_price, position.quantity, position.entry_time,
                      position.unrealized_pnl, position.unrealized_pnl_pct))
                conn.commit()
                
        except Exception as e:
            log_error("TradingHistory", e, "_add_position")
    
    def _update_position(self, symbol: str, position: Position):
        """Обновление существующей позиции"""
        try:
            self.positions[symbol] = position
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE positions 
                    SET current_price=?, quantity=?, unrealized_pnl=?, unrealized_pnl_pct=?
                    WHERE symbol=?
                """, (position.current_price, position.quantity, 
                      position.unrealized_pnl, position.unrealized_pnl_pct, symbol))
                conn.commit()
                
        except Exception as e:
            log_error("TradingHistory", e, "_update_position")
    
    def _close_position(self, symbol: str):
        """Закрытие позиции"""
        try:
            if symbol in self.positions:
                del self.positions[symbol]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM positions WHERE symbol=?", (symbol,))
                conn.commit()
                
        except Exception as e:
            log_error("TradingHistory", e, "_close_position")
    
    def update_position_prices(self, price_updates: Dict[str, float]):
        """Обновление текущих цен позиций"""
        try:
            for symbol, current_price in price_updates.items():
                if symbol in self.positions:
                    position = self.positions[symbol]
                    position.current_price = current_price
                    position.update_pnl()
                    self._update_position(symbol, position)
                    
        except Exception as e:
            log_error("TradingHistory", e, "update_position_prices")
    
    def get_current_positions(self) -> List[Position]:
        """Получение всех активных позиций"""
        try:
            # Load positions from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM positions")
                rows = cursor.fetchall()
                
                positions = []
                for row in rows:
                    position = Position(
                        symbol=row[0],
                        position_type=row[1],
                        entry_price=row[2],
                        current_price=row[3],
                        quantity=row[4],
                        entry_time=datetime.fromisoformat(row[5]),
                        unrealized_pnl=row[6],
                        unrealized_pnl_pct=row[7]
                    )
                    positions.append(position)
                    self.positions[position.symbol] = position
                
                return positions
                
        except Exception as e:
            log_error("TradingHistory", e, "get_current_positions")
            return []
    
    def get_trade_history(self, start_date: datetime = None, end_date: datetime = None, 
                         symbol: str = None, limit: int = 100) -> List[Trade]:
        """Получение истории сделок"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM trades WHERE 1=1"
                params = []
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                trades = []
                for row in rows:
                    analysis_data = json.loads(row[8]) if row[8] else {}
                    trade = Trade(
                        id=row[0],
                        symbol=row[1],
                        trade_type=row[2],
                        quantity=row[3],
                        price=row[4],
                        timestamp=datetime.fromisoformat(row[5]),
                        pnl=row[6],
                        fee=row[7],
                        analysis_data=analysis_data
                    )
                    trades.append(trade)
                
                return trades
                
        except Exception as e:
            log_error("TradingHistory", e, "get_trade_history")
            return []
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """Получение сводки по производительности"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            trades = self.get_trade_history(start_date=start_date, end_date=end_date, limit=1000)
            
            if not trades:
                return {
                    'total_trades': 0,
                    'profitable_trades': 0,
                    'total_pnl': 0,
                    'win_rate': 0,
                    'avg_profit': 0,
                    'avg_loss': 0,
                    'max_profit': 0,
                    'max_loss': 0,
                    'total_fees': 0
                }
            
            # Calculate metrics
            total_trades = len(trades)
            profitable_trades = len([t for t in trades if t.pnl > 0])
            total_pnl = sum(t.pnl for t in trades)
            total_fees = sum(t.fee for t in trades)
            win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
            
            profits = [t.pnl for t in trades if t.pnl > 0]
            losses = [t.pnl for t in trades if t.pnl < 0]
            
            avg_profit = sum(profits) / len(profits) if profits else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            max_profit = max(profits) if profits else 0
            max_loss = min(losses) if losses else 0
            
            return {
                'total_trades': total_trades,
                'profitable_trades': profitable_trades,
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'total_fees': total_fees,
                'net_pnl': total_pnl - total_fees
            }
            
        except Exception as e:
            log_error("TradingHistory", e, "get_performance_summary")
            return {}
    
    def calculate_sharpe_ratio(self, days: int = 30) -> float:
        """Расчет коэффициента Шарпа"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get daily returns
            daily_returns = self._get_daily_returns(start_date, end_date)
            
            if len(daily_returns) < 2:
                return 0.0
            
            # Calculate Sharpe ratio
            avg_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            
            if std_return == 0:
                return 0.0
            
            # Assuming risk-free rate of 2% annually (0.0055% daily)
            risk_free_rate = 0.000055
            sharpe_ratio = (avg_return - risk_free_rate) / std_return
            
            # Annualize (multiply by sqrt(365))
            return sharpe_ratio * (365 ** 0.5)
            
        except Exception as e:
            log_error("TradingHistory", e, "calculate_sharpe_ratio")
            return 0.0
    
    def _get_daily_returns(self, start_date: datetime, end_date: datetime) -> List[float]:
        """Получение дневной доходности"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DATE(timestamp) as trade_date, SUM(pnl - fee) as daily_pnl
                    FROM trades 
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY DATE(timestamp)
                    ORDER BY trade_date
                """, (start_date, end_date))
                
                rows = cursor.fetchall()
                
                # Convert to returns (assuming starting capital of $10,000)
                starting_capital = 10000
                daily_returns = []
                
                for row in rows:
                    daily_pnl = row[1]
                    daily_return = daily_pnl / starting_capital
                    daily_returns.append(daily_return)
                
                return daily_returns
                
        except Exception as e:
            log_error("TradingHistory", e, "_get_daily_returns")
            return []
    
    def calculate_max_drawdown(self, days: int = 30) -> float:
        """Расчет максимальной просадки"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            trades = self.get_trade_history(start_date=start_date, end_date=end_date, limit=1000)
            
            if not trades:
                return 0.0
            
            # Calculate cumulative P&L
            cumulative_pnl = []
            running_total = 0
            
            for trade in reversed(trades):  # Reverse to get chronological order
                running_total += (trade.pnl - trade.fee)
                cumulative_pnl.append(running_total)
            
            if not cumulative_pnl:
                return 0.0
            
            # Calculate drawdown
            peak = cumulative_pnl[0]
            max_drawdown = 0
            
            for value in cumulative_pnl:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / abs(peak) if peak != 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown * 100  # Return as percentage
            
        except Exception as e:
            log_error("TradingHistory", e, "calculate_max_drawdown")
            return 0.0
    
    def export_to_csv(self, filename: str, start_date: datetime = None, 
                     end_date: datetime = None) -> bool:
        """Экспорт истории в CSV файл"""
        try:
            trades = self.get_trade_history(start_date=start_date, end_date=end_date, limit=10000)
            
            if not trades:
                logger.warning("No trades to export")
                return False
            
            # Convert to DataFrame
            data = []
            for trade in trades:
                data.append({
                    'ID': trade.id,
                    'Symbol': trade.symbol,
                    'Type': trade.trade_type,
                    'Quantity': trade.quantity,
                    'Price': trade.price,
                    'Timestamp': trade.timestamp.isoformat(),
                    'PnL': trade.pnl,
                    'Fee': trade.fee,
                    'Net PnL': trade.pnl - trade.fee
                })
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            
            logger.info(f"Trading history exported to {filename}")
            return True
            
        except Exception as e:
            log_error("TradingHistory", e, "export_to_csv")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 365):
        """Очистка старых данных"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old trades
                cursor.execute("DELETE FROM trades WHERE timestamp < ?", (cutoff_date,))
                deleted_trades = cursor.rowcount
                
                # Delete old performance metrics
                cursor.execute("DELETE FROM performance_metrics WHERE date < ?", (cutoff_date.date(),))
                deleted_metrics = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_trades} old trades and {deleted_metrics} old metrics")
                
        except Exception as e:
            log_error("TradingHistory", e, "cleanup_old_data")
