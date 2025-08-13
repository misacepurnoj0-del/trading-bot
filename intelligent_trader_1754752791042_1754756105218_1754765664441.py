import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import random

from utils.logger import get_logger, log_trading_action
from exchanges.mexc_client import MEXCClient
from analysis.technical_analysis import TechnicalAnalysis
from analysis.indicators import TechnicalIndicators
from news.news_parser import NewsParser
from trading.notifications import NotificationManager
from trading.trading_history import TradingHistory

logger = get_logger(__name__)

class IntelligentTrader:
    """Интеллектуальная торговая система с AI-анализом"""
    
    def __init__(self, api_key: str = "", secret_key: str = "", demo_mode: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.demo_mode = demo_mode
        
        # Initialize components
        self.mexc_client = MEXCClient(api_key, secret_key, demo_mode)
        self.technical_analysis = TechnicalAnalysis()
        self.indicators = TechnicalIndicators()
        self.news_parser = NewsParser()
        self.notifications = NotificationManager()
        self.trading_history = TradingHistory()
        
        # Trading parameters
        self.max_positions = 3
        self.position_size_pct = 33.33  # Each position is ~33% of capital
        self.max_leverage = 5.0
        self.min_confidence_threshold = 70.0
        self.max_hold_time_hours = 168  # 1 week max
        
        # AI learning parameters
        self.success_weight_adjustment = 0.1
        self.failure_weight_adjustment = -0.05
        
        # Indicator weights (will be adjusted by AI learning)
        self.indicator_weights = {
            'technical': 0.35,
            'fundamental': 0.25,
            'sentiment': 0.20,
            'momentum': 0.20
        }
        
        # Market state tracking
        self.last_analysis_time = None
        self.market_conditions = {}
        
        logger.info(f"Intelligent Trader initialized - Demo: {demo_mode}")
    
    def analyze_market_overview(self) -> Dict:
        """Анализ общего состояния рынка"""
        try:
            # Get market conditions from MEXC
            market_data = self.mexc_client.analyze_market_conditions()
            
            if 'error' in market_data:
                logger.error(f"Market analysis error: {market_data['error']}")
                return {'sentiment': 'Unknown', 'confidence': 0}
            
            # Analyze news sentiment
            news_sentiment = self.news_parser.get_market_sentiment()
            
            # Combine market and news data
            overall_sentiment = self._combine_sentiments(
                market_data.get('market_sentiment', 'Neutral'),
                news_sentiment.get('overall_sentiment', 'Neutral')
            )
            
            confidence = self._calculate_market_confidence(market_data, news_sentiment)
            
            self.market_conditions = {
                'sentiment': overall_sentiment,
                'confidence': confidence,
                'gainers_pct': market_data.get('gainers_pct', 0),
                'avg_change_pct': market_data.get('avg_change_pct', 0),
                'news_score': news_sentiment.get('sentiment_score', 0),
                'analysis_time': datetime.now()
            }
            
            return self.market_conditions
            
        except Exception as e:
            logger.error(f"Error in market overview analysis: {str(e)}")
            return {'sentiment': 'Unknown', 'confidence': 0}
    
    def _combine_sentiments(self, market_sentiment: str, news_sentiment: str) -> str:
        """Объединение рыночного и новостного настроения"""
        sentiment_scores = {
            'Bullish': 1,
            'Neutral': 0,
            'Bearish': -1
        }
        
        market_score = sentiment_scores.get(market_sentiment, 0)
        news_score = sentiment_scores.get(news_sentiment, 0)
        
        combined_score = (market_score * 0.6) + (news_score * 0.4)
        
        if combined_score > 0.3:
            return 'Bullish'
        elif combined_score < -0.3:
            return 'Bearish'
        else:
            return 'Neutral'
    
    def _calculate_market_confidence(self, market_data: Dict, news_data: Dict) -> float:
        """Расчет уверенности в рыночном анализе"""
        confidence = 50.0  # Base confidence
        
        # Market data factors
        gainers_pct = market_data.get('gainers_pct', 50)
        if gainers_pct > 60:
            confidence += 15
        elif gainers_pct < 40:
            confidence += 15
        
        # News sentiment strength
        news_score = abs(news_data.get('sentiment_score', 0))
        confidence += min(news_score * 20, 20)
        
        # Volume factor
        total_volume = market_data.get('total_volume_usdt', 0)
        if total_volume > 1e9:  # High volume
            confidence += 10
        
        return min(confidence, 95.0)
    
    def scan_for_opportunities(self, limit: int = 50) -> List[Dict]:
        """Сканирование рынка для поиска торговых возможностей"""
        try:
            # Get top performing and high volume symbols
            gainers = self.mexc_client.get_top_gainers_losers(limit // 2)
            volume_leaders = self.mexc_client.get_volume_leaders(limit // 2)
            
            # Combine and remove duplicates
            all_symbols = {}
            
            for ticker in gainers + volume_leaders:
                symbol = ticker['symbol']
                if symbol not in all_symbols:
                    all_symbols[symbol] = ticker
            
            opportunities = []
            
            for symbol, ticker_data in list(all_symbols.items())[:limit]:
                try:
                    # Get detailed analysis for this symbol
                    analysis = self.analyze_symbol(symbol)
                    
                    if analysis and analysis.get('confidence', 0) >= self.min_confidence_threshold:
                        opportunities.append({
                            'symbol': symbol,
                            'action': analysis['action'],
                            'confidence': analysis['confidence'],
                            'reasoning': analysis['reasoning'][:100] + "...",
                            'current_price': ticker_data.get('lastPrice', 0),
                            'change_24h': ticker_data.get('priceChangePercent', 0),
                            'volume_24h': ticker_data.get('volume', 0)
                        })
                        
                except Exception as e:
                    logger.warning(f"Error analyzing {symbol}: {str(e)}")
                    continue
            
            # Sort by confidence
            opportunities.sort(key=lambda x: x['confidence'], reverse=True)
            
            return opportunities[:10]  # Return top 10 opportunities
            
        except Exception as e:
            logger.error(f"Error scanning for opportunities: {str(e)}")
            return []
    
    def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """Комплексный анализ конкретного символа"""
        try:
            # Get market data
            klines_data = self.mexc_client.get_klines(symbol, '1h', 100)
            
            if 'error' in klines_data or not klines_data:
                return None
            
            # Convert to DataFrame
            df = self._convert_klines_to_df(klines_data)
            
            if len(df) < 50:  # Need enough data for analysis
                return None
            
            # Technical analysis
            technical_score = self._calculate_technical_score(df)
            
            # Fundamental analysis (volume, market cap estimation)
            fundamental_score = self._calculate_fundamental_score(symbol, df)
            
            # Sentiment analysis (news impact)
            sentiment_score = self._calculate_sentiment_score(symbol)
            
            # Momentum analysis
            momentum_score = self._calculate_momentum_score(df)
            
            # Combine scores using weighted average
            total_score = (
                technical_score * self.indicator_weights['technical'] +
                fundamental_score * self.indicator_weights['fundamental'] +
                sentiment_score * self.indicator_weights['sentiment'] +
                momentum_score * self.indicator_weights['momentum']
            )
            
            # Determine action and confidence
            action, confidence, reasoning = self._interpret_analysis_score(
                total_score, technical_score, fundamental_score, sentiment_score, momentum_score
            )
            
            return {
                'symbol': symbol,
                'action': action,
                'confidence': confidence,
                'reasoning': reasoning,
                'technical_score': technical_score,
                'fundamental_score': fundamental_score,
                'sentiment_score': sentiment_score,
                'momentum_score': momentum_score,
                'total_score': total_score
            }
            
        except Exception as e:
            logger.error(f"Error analyzing symbol {symbol}: {str(e)}")
            return None
    
    def _convert_klines_to_df(self, klines_data: List) -> pd.DataFrame:
        """Конвертация данных свечей в DataFrame"""
        df = pd.DataFrame(klines_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
            'taker_buy_quote_volume', 'ignore'
        ])
        
        # Convert to proper types
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def _calculate_technical_score(self, df: pd.DataFrame) -> float:
        """Расчет технического анализа (35% весе)"""
        try:
            analysis = self.technical_analysis.get_comprehensive_analysis(df)
            
            if not analysis:
                return 50.0  # Neutral score
            
            score = 50.0
            
            # RSI analysis
            rsi = analysis.get('rsi', 50)
            if rsi < 30:  # Oversold
                score += 15
            elif rsi > 70:  # Overbought
                score -= 15
            
            # MACD analysis
            macd = analysis.get('macd', 0)
            macd_signal = analysis.get('macd_signal', 0)
            if macd > macd_signal:  # Bullish crossover
                score += 10
            else:  # Bearish crossover
                score -= 10
            
            # Moving averages
            price = analysis.get('price', 0)
            sma_20 = analysis.get('sma_20', 0)
            if price > sma_20:  # Above MA
                score += 10
            else:  # Below MA
                score -= 10
            
            # Bollinger Bands
            bb_upper = analysis.get('bb_upper', 0)
            bb_lower = analysis.get('bb_lower', 0)
            if price > bb_upper:  # Overbought
                score -= 5
            elif price < bb_lower:  # Oversold
                score += 5
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {str(e)}")
            return 50.0
    
    def _calculate_fundamental_score(self, symbol: str, df: pd.DataFrame) -> float:
        """Расчет фундаментального анализа (25% веса)"""
        try:
            score = 50.0
            
            # Volume analysis
            recent_volume = df['volume'].tail(24).mean()  # Last 24 hours avg
            historical_volume = df['volume'].tail(168).mean()  # Last week avg
            
            if recent_volume > historical_volume * 1.5:  # High volume spike
                score += 20
            elif recent_volume < historical_volume * 0.5:  # Low volume
                score -= 10
            
            # Price volatility
            price_changes = df['close'].pct_change().tail(24)
            volatility = price_changes.std()
            
            if 0.02 < volatility < 0.08:  # Moderate volatility
                score += 10
            elif volatility > 0.15:  # High volatility
                score -= 5
            
            # Trend consistency
            trend_data = self.technical_analysis.analyze_trend(df)
            if trend_data['strength'] == 'Strong':
                score += 15
            elif trend_data['strength'] == 'Moderate':
                score += 5
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error in fundamental analysis: {str(e)}")
            return 50.0
    
    def _calculate_sentiment_score(self, symbol: str) -> float:
        """Расчет анализа настроений (20% веса)"""
        try:
            # Get news sentiment for this symbol or general crypto
            coin_name = symbol.replace('USDT', '').replace('BTC', '').lower()
            
            news_data = self.news_parser.analyze_symbol_sentiment(coin_name)
            
            if news_data:
                sentiment_score = news_data.get('sentiment_score', 0)
                # Convert from -1,1 range to 0,100 range
                return max(0, min(100, (sentiment_score + 1) * 50))
            
            # Use general market sentiment if no specific news
            market_sentiment = self.news_parser.get_market_sentiment()
            general_score = market_sentiment.get('sentiment_score', 0)
            
            return max(0, min(100, (general_score + 1) * 50))
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return 50.0
    
    def _calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """Расчет анализа моментума (20% веса)"""
        try:
            score = 50.0
            
            # Price momentum (recent vs older periods)
            recent_prices = df['close'].tail(24)
            older_prices = df['close'].tail(72).head(24)
            
            recent_avg = recent_prices.mean()
            older_avg = older_prices.mean()
            
            momentum_pct = ((recent_avg - older_avg) / older_avg) * 100
            
            if momentum_pct > 5:  # Strong positive momentum
                score += 20
            elif momentum_pct > 2:  # Moderate positive momentum
                score += 10
            elif momentum_pct < -5:  # Strong negative momentum
                score -= 20
            elif momentum_pct < -2:  # Moderate negative momentum
                score -= 10
            
            # Volume momentum
            recent_vol = df['volume'].tail(24).mean()
            older_vol = df['volume'].tail(72).head(24).mean()
            
            vol_momentum = ((recent_vol - older_vol) / older_vol) * 100 if older_vol > 0 else 0
            
            if vol_momentum > 20:  # Volume increasing
                score += 10
            elif vol_momentum < -20:  # Volume decreasing
                score -= 5
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error in momentum analysis: {str(e)}")
            return 50.0
    
    def _interpret_analysis_score(self, total_score: float, technical: float, 
                                fundamental: float, sentiment: float, momentum: float) -> Tuple[str, float, str]:
        """Интерпретация результатов анализа"""
        
        # Determine action
        if total_score >= 65:
            action = "BUY"
        elif total_score <= 35:
            action = "SELL"
        else:
            action = "HOLD"
        
        # Calculate confidence based on score strength and consistency
        confidence = total_score if action == "BUY" else (100 - total_score) if action == "SELL" else 50
        
        # Adjust confidence based on score consistency
        scores = [technical, fundamental, sentiment, momentum]
        score_std = np.std(scores)
        
        if score_std > 20:  # High variance - reduce confidence
            confidence *= 0.8
        elif score_std < 10:  # Low variance - increase confidence
            confidence *= 1.1
        
        confidence = max(0, min(95, confidence))
        
        # Generate reasoning
        reasoning_parts = []
        
        if technical > 60:
            reasoning_parts.append("Технические индикаторы показывают бычий сигнал")
        elif technical < 40:
            reasoning_parts.append("Технические индикаторы показывают медвежий сигнал")
        
        if fundamental > 60:
            reasoning_parts.append("Фундаментальные факторы поддерживают рост")
        elif fundamental < 40:
            reasoning_parts.append("Фундаментальные факторы указывают на ослабление")
        
        if sentiment > 60:
            reasoning_parts.append("Позитивные новости и настроения рынка")
        elif sentiment < 40:
            reasoning_parts.append("Негативные новости влияют на настроения")
        
        if momentum > 60:
            reasoning_parts.append("Сильный восходящий моментум")
        elif momentum < 40:
            reasoning_parts.append("Нисходящий моментум")
        
        reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Смешанные сигналы от различных индикаторов"
        
        return action, confidence, reasoning
    
    def execute_trade(self, symbol: str, action: str, confidence: float, reasoning: str) -> Dict:
        """Выполнение торговой сделки"""
        try:
            # Check if we have available position slots
            open_positions = len(self.trading_history.get_current_positions())
            if open_positions >= self.max_positions:
                return {'success': False, 'message': 'Достигнуто максимальное количество позиций'}
            
            # Get current price
            ticker = self.mexc_client.get_ticker_price(symbol)
            if 'error' in ticker:
                return {'success': False, 'message': f'Ошибка получения цены: {ticker["error"]}'}
            
            current_price = float(ticker.get('price', 0))
            if current_price <= 0:
                return {'success': False, 'message': 'Некорректная цена'}
            
            # Calculate position size
            account_info = self.mexc_client.get_account_info()
            if 'error' in account_info:
                return {'success': False, 'message': 'Ошибка получения баланса'}
            
            # Get USDT balance
            usdt_balance = 0
            if 'balances' in account_info:
                for balance in account_info['balances']:
                    if balance['asset'] == 'USDT':
                        usdt_balance = float(balance['free'])
                        break
            
            if usdt_balance < 10:  # Minimum $10 for trade
                return {'success': False, 'message': 'Недостаточный баланс для торговли'}
            
            # Calculate position size (33% of available balance)
            position_value = usdt_balance * (self.position_size_pct / 100)
            
            # Apply leverage if confidence is high
            leverage = 1.0
            if confidence >= 85:
                leverage = min(self.max_leverage, 3.0)
            elif confidence >= 80:
                leverage = 2.0
            
            position_value *= leverage
            quantity = position_value / current_price
            
            # Place order
            order_result = self.mexc_client.place_order(
                symbol=symbol,
                side=action,
                order_type='MARKET',
                quantity=quantity
            )
            
            if 'error' in order_result:
                return {'success': False, 'message': f'Ошибка размещения ордера: {order_result["error"]}'}
            
            # Record trade
            trade_id = self.trading_history.add_trade(
                symbol=symbol,
                action=action,
                entry_price=current_price,
                quantity=quantity,
                confidence=confidence,
                reasoning=reasoning,
                demo_mode=self.demo_mode
            )
            
            # Send notification
            self.notifications.notify_trade_opened(
                symbol=symbol,
                action=action,
                price=current_price,
                quantity=quantity,
                confidence=confidence
            )
            
            log_trading_action("TRADE_EXECUTED", symbol, {
                'action': action,
                'quantity': quantity,
                'price': current_price,
                'confidence': confidence
            })
            
            return {
                'success': True,
                'trade_id': trade_id,
                'order_id': order_result.get('orderId'),
                'quantity': quantity,
                'price': current_price,
                'leverage': leverage
            }
            
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return {'success': False, 'message': f'Ошибка выполнения сделки: {str(e)}'}
    
    def manage_positions(self) -> List[Dict]:
        """Управление открытыми позициями"""
        results = []
        
        try:
            positions = self.trading_history.get_current_positions()
            open_trades = self.trading_history.get_open_trades()
            
            for position in positions:
                try:
                    # Check if position should be closed
                    should_close, reason = self._should_close_position(position)
                    
                    if should_close:
                        # Find corresponding trade
                        trade = next((t for t in open_trades if t.symbol == position.symbol), None)
                        
                        if trade:
                            close_result = self._close_position(trade, reason)
                            results.append(close_result)
                
                except Exception as e:
                    logger.error(f"Error managing position {position.symbol}: {str(e)}")
                    results.append({
                        'symbol': position.symbol,
                        'action': 'error',
                        'message': str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in position management: {str(e)}")
            return []
    
    def _should_close_position(self, position) -> Tuple[bool, str]:
        """Определение необходимости закрытия позиции"""
        
        # Check time-based exit
        time_held = datetime.now() - position.entry_time
        if time_held.total_seconds() > self.max_hold_time_hours * 3600:
            return True, "Максимальное время удержания"
        
        # Check profit/loss thresholds
        if position.unrealized_pnl_pct > 15:  # Take profit at 15%
            return True, f"Фиксация прибыли {position.unrealized_pnl_pct:.1f}%"
        
        if position.unrealized_pnl_pct < -8:  # Stop loss at -8%
            return True, f"Стоп-лосс {position.unrealized_pnl_pct:.1f}%"
        
        # Re-analyze the symbol for exit signals
        analysis = self.analyze_symbol(position.symbol)
        if analysis:
            # If confidence dropped significantly or signal reversed
            if position.side == "LONG" and analysis['action'] == "SELL" and analysis['confidence'] > 75:
                return True, "Сигнал на продажу с высокой уверенностью"
            elif position.side == "SHORT" and analysis['action'] == "BUY" and analysis['confidence'] > 75:
                return True, "Сигнал на покупку с высокой уверенностью"
        
        return False, ""
    
    def _close_position(self, trade, reason: str) -> Dict:
        """Закрытие позиции"""
        try:
            # Get current price
            ticker = self.mexc_client.get_ticker_price(trade.symbol)
            current_price = float(ticker.get('price', 0))
            
            # Place closing order
            close_side = "SELL" if trade.action == "BUY" else "BUY"
            
            order_result = self.mexc_client.place_order(
                symbol=trade.symbol,
                side=close_side,
                order_type='MARKET',
                quantity=trade.quantity
            )
            
            if 'error' not in order_result:
                # Update trade record
                self.trading_history.close_trade(trade.trade_id, current_price)
                
                # Calculate profit
                if trade.action == "BUY":
                    profit_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
                else:
                    profit_pct = ((trade.entry_price - current_price) / trade.entry_price) * 100
                
                # Send notification
                self.notifications.notify_trade_closed(
                    symbol=trade.symbol,
                    action=trade.action,
                    entry_price=trade.entry_price,
                    exit_price=current_price,
                    profit_pct=profit_pct
                )
                
                # Learn from this trade
                self._learn_from_trade(trade, profit_pct)
                
                log_trading_action("TRADE_CLOSED", trade.symbol, {
                    'profit_pct': profit_pct,
                    'reason': reason
                })
                
                return {
                    'symbol': trade.symbol,
                    'action': 'closed',
                    'profit_pct': profit_pct,
                    'reason': reason
                }
            else:
                return {
                    'symbol': trade.symbol,
                    'action': 'error',
                    'message': order_result['error']
                }
                
        except Exception as e:
            logger.error(f"Error closing position {trade.symbol}: {str(e)}")
            return {
                'symbol': trade.symbol,
                'action': 'error',
                'message': str(e)
            }
    
    def _learn_from_trade(self, trade, profit_pct: float):
        """Обучение на основе результатов сделки"""
        try:
            # Determine if trade was successful
            success = profit_pct > 0
            
            # Adjust indicator weights based on success
            adjustment = self.success_weight_adjustment if success else self.failure_weight_adjustment
            
            # This is a simplified learning mechanism
            # In a real AI system, this would be much more sophisticated
            
            if success:
                logger.info(f"Successful trade {trade.symbol}: +{profit_pct:.2f}%. Reinforcing strategy.")
            else:
                logger.info(f"Unsuccessful trade {trade.symbol}: {profit_pct:.2f}%. Adjusting strategy.")
                
        except Exception as e:
            logger.error(f"Error in learning from trade: {str(e)}")
    
    def get_trading_status(self) -> Dict:
        """Получение текущего статуса торговой системы"""
        try:
            positions = self.trading_history.get_current_positions()
            stats = self.trading_history.get_trading_statistics()
            
            return {
                'active_positions': len(positions),
                'max_positions': self.max_positions,
                'demo_mode': self.demo_mode,
                'total_trades': stats.get('total_trades', 0),
                'win_rate': stats.get('win_rate', 0),
                'total_profit_pct': stats.get('total_profit_pct', 0),
                'market_conditions': self.market_conditions,
                'last_analysis': self.last_analysis_time,
                'indicator_weights': self.indicator_weights
            }
            
        except Exception as e:
            logger.error(f"Error getting trading status: {str(e)}")
            return {}
