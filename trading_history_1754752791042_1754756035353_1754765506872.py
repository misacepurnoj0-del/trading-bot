from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import pandas as pd
import json
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class TradeRecord:
    trade_id: str
    symbol: str
    action: str  # BUY, SELL
    entry_time: datetime
    entry_price: float
    quantity: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_pct: Optional[float] = None
    status: str = "OPEN"  # OPEN, CLOSED, CANCELLED
    confidence: float = 0.0
    reasoning: str = ""
    exchange: str = "MEXC"
    fees: float = 0.0
    demo_mode: bool = True

@dataclass
class Position:
    symbol: str
    side: str  # LONG, SHORT
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_time: datetime
    exchange: str = "MEXC"

class TradingHistory:
    """Менеджер истории торговли и позиций"""
    
    def __init__(self):
        self.trades: List[TradeRecord] = []
        self.positions: List[Position] = []
        
    def add_trade(self, 
                  symbol: str,
                  action: str,
                  entry_price: float,
                  quantity: float,
                  confidence: float = 0.0,
                  reasoning: str = "",
                  exchange: str = "MEXC",
                  demo_mode: bool = True) -> str:
        """Добавить новую сделку"""
        
        trade_id = f"{symbol}_{action}_{int(datetime.now().timestamp())}"
        
        trade = TradeRecord(
            trade_id=trade_id,
            symbol=symbol,
            action=action,
            entry_time=datetime.now(),
            entry_price=entry_price,
            quantity=quantity,
            confidence=confidence,
            reasoning=reasoning,
            exchange=exchange,
            demo_mode=demo_mode
        )
        
        self.trades.append(trade)
        
        # Добавляем позицию если это покупка
        if action == "BUY":
            self.add_position(symbol, "LONG", quantity, entry_price, exchange)
        
        logger.info(f"Добавлена сделка: {trade_id}")
        return trade_id
    
    def close_trade(self, trade_id: str, exit_price: float, fees: float = 0.0) -> bool:
        """Закрыть сделку"""
        
        for trade in self.trades:
            if trade.trade_id == trade_id and trade.status == "OPEN":
                trade.exit_time = datetime.now()
                trade.exit_price = exit_price
                trade.fees = fees
                trade.status = "CLOSED"
                
                # Рассчитываем прибыль/убыток
                if trade.action == "BUY":
                    trade.profit_loss = (exit_price - trade.entry_price) * trade.quantity - fees
                else:  # SELL
                    trade.profit_loss = (trade.entry_price - exit_price) * trade.quantity - fees
                
                trade.profit_pct = (trade.profit_loss / (trade.entry_price * trade.quantity)) * 100
                
                # Удаляем позицию
                self.remove_position(trade.symbol)
                
                logger.info(f"Закрыта сделка: {trade_id}, P&L: {trade.profit_pct:.2f}%")
                return True
        
        return False
    
    def add_position(self, symbol: str, side: str, quantity: float, entry_price: float, exchange: str = "MEXC"):
        """Добавить позицию"""
        
        # Удаляем существующую позицию по этому символу
        self.positions = [p for p in self.positions if p.symbol != symbol]
        
        position = Position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            entry_time=datetime.now(),
            exchange=exchange
        )
        
        self.positions.append(position)
        logger.info(f"Добавлена позиция: {symbol} {side}")
    
    def remove_position(self, symbol: str):
        """Удалить позицию"""
        
        initial_count = len(self.positions)
        self.positions = [p for p in self.positions if p.symbol != symbol]
        
        if len(self.positions) < initial_count:
            logger.info(f"Удалена позиция: {symbol}")
    
    def update_position_prices(self, price_updates: Dict[str, float]):
        """Обновить текущие цены позиций"""
        
        for position in self.positions:
            if position.symbol in price_updates:
                position.current_price = price_updates[position.symbol]
                
                # Рассчитываем нереализованную прибыль
                if position.side == "LONG":
                    position.unrealized_pnl = (position.current_price - position.entry_price) * position.quantity
                else:  # SHORT
                    position.unrealized_pnl = (position.entry_price - position.current_price) * position.quantity
                
                position.unrealized_pnl_pct = (position.unrealized_pnl / (position.entry_price * position.quantity)) * 100
    
    def get_open_trades(self) -> List[TradeRecord]:
        """Получить открытые сделки"""
        return [trade for trade in self.trades if trade.status == "OPEN"]
    
    def get_closed_trades(self, limit: Optional[int] = None) -> List[TradeRecord]:
        """Получить закрытые сделки"""
        
        closed_trades = [trade for trade in self.trades if trade.status == "CLOSED"]
        closed_trades.sort(key=lambda x: x.exit_time, reverse=True)
        
        if limit:
            return closed_trades[:limit]
        
        return closed_trades
    
    def get_current_positions(self) -> List[Position]:
        """Получить текущие позиции"""
        return self.positions.copy()
    
    def get_trading_statistics(self, days: Optional[int] = None) -> Dict:
        """Получить статистику торговли"""
        
        # Фильтруем сделки по дням если указано
        trades = self.trades
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            trades = [t for t in trades if t.entry_time >= cutoff_date]
        
        closed_trades = [t for t in trades if t.status == "CLOSED"]
        
        if not closed_trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_profit_pct": 0.0,
                "avg_profit_pct": 0.0,
                "best_trade_pct": 0.0,
                "worst_trade_pct": 0.0,
                "avg_hold_time_hours": 0.0
            }
        
        # Основная статистика
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t.profit_pct > 0]
        win_rate = (len(winning_trades) / total_trades) * 100
        
        # Прибыльность
        total_profit_pct = sum(t.profit_pct for t in closed_trades if t.profit_pct)
        avg_profit_pct = total_profit_pct / total_trades
        
        profit_pcts = [t.profit_pct for t in closed_trades if t.profit_pct is not None]
        best_trade_pct = max(profit_pcts) if profit_pcts else 0.0
        worst_trade_pct = min(profit_pcts) if profit_pcts else 0.0
        
        # Время удержания
        hold_times = []
        for trade in closed_trades:
            if trade.exit_time and trade.entry_time:
                hold_time = trade.exit_time - trade.entry_time
                hold_times.append(hold_time.total_seconds() / 3600)  # в часах
        
        avg_hold_time_hours = sum(hold_times) / len(hold_times) if hold_times else 0.0
        
        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_profit_pct": total_profit_pct,
            "avg_profit_pct": avg_profit_pct,
            "best_trade_pct": best_trade_pct,
            "worst_trade_pct": worst_trade_pct,
            "avg_hold_time_hours": avg_hold_time_hours,
            "winning_trades": len(winning_trades),
            "losing_trades": total_trades - len(winning_trades)
        }
    
    def get_portfolio_value(self) -> Dict:
        """Получить общую стоимость портфеля"""
        
        total_unrealized_pnl = sum(p.unrealized_pnl for p in self.positions)
        total_position_value = sum(p.current_price * p.quantity for p in self.positions)
        
        return {
            "total_positions": len(self.positions),
            "total_position_value": total_position_value,
            "total_unrealized_pnl": total_unrealized_pnl,
            "positions": [asdict(p) for p in self.positions]
        }
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """Экспорт истории в DataFrame"""
        
        if not self.trades:
            return pd.DataFrame()
        
        trade_dicts = []
        for trade in self.trades:
            trade_dict = asdict(trade)
            trade_dict['entry_time'] = trade.entry_time.isoformat()
            if trade.exit_time:
                trade_dict['exit_time'] = trade.exit_time.isoformat()
            trade_dicts.append(trade_dict)
        
        return pd.DataFrame(trade_dicts)
    
    def get_performance_chart_data(self) -> Dict:
        """Получить данные для графика производительности"""
        
        closed_trades = self.get_closed_trades()
        if not closed_trades:
            return {"dates": [], "cumulative_profit": [], "trade_profits": []}
        
        dates = []
        cumulative_profit = []
        trade_profits = []
        
        running_profit = 0.0
        
        for trade in reversed(closed_trades):  # От старых к новым
            if trade.exit_time and trade.profit_pct is not None:
                dates.append(trade.exit_time.strftime('%Y-%m-%d %H:%M'))
                running_profit += trade.profit_pct
                cumulative_profit.append(running_profit)
                trade_profits.append(trade.profit_pct)
        
        return {
            "dates": dates,
            "cumulative_profit": cumulative_profit,
            "trade_profits": trade_profits
        }
    
    def clear_demo_trades(self):
        """Очистить демо-сделки"""
        
        demo_count = len([t for t in self.trades if t.demo_mode])
        self.trades = [t for t in self.trades if not t.demo_mode]
        self.positions = []  # Очищаем все позиции при очистке демо
        
        logger.info(f"Очищено {demo_count} демо-сделок")
        return demo_count
