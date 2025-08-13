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
            
            # Moderate volatility is good for trading
            if 0.02 <= volatility <= 0.05:  # 2-5% volatility
                score += 10
            elif volatility > 0.1:  # Too volatile
                score -= 15
            
            # Market cap consideration (for USDT pairs)
            if symbol.endswith('USDT'):
                # Assume larger market cap coins are more stable
                base_asset = symbol.replace('USDT', '')
                if base_asset in ['BTC', 'ETH', 'BNB']:  # Top tier
                    score += 10
                elif base_asset in ['ADA', 'XRP', 'SOL', 'DOT']:  # Second tier
                    score += 5
                else:  # Altcoins - higher risk
                    score -= 5
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error in fundamental analysis: {str(e)}")
            return 50.0
    
    def _calculate_sentiment_score(self, symbol: str) -> float:
        """Расчет анализа настроений (20% веса)"""
        try:
            score = 50.0
            
            # Get symbol-specific news
            symbol_news = self.news_parser.get_symbol_news(symbol, 24)
            
            if symbol_news:
                # If there's specific news, analyze it
                positive_news = 0
                negative_news = 0
                
                for news_item in symbol_news:
                    title = news_item.get('title', '').lower()
                    description = news_item.get('description', '').lower()
                    text = f"{title} {description}"
                    
                    # Simple sentiment analysis
                    positive_keywords = ['gain', 'rise', 'up', 'bull', 'positive', 'growth', 'adoption']
                    negative_keywords = ['fall', 'down', 'bear', 'negative', 'crash', 'decline', 'drop']
                    
                    if any(keyword in text for keyword in positive_keywords):
                        positive_news += 1
                    elif any(keyword in text for keyword in negative_keywords):
                        negative_news += 1
                
                if positive_news > negative_news:
                    score += min(positive_news * 10, 30)
                elif negative_news > positive_news:
                    score -= min(negative_news * 10, 30)
            else:
                # Use general market sentiment
                market_sentiment = self.news_parser.get_market_sentiment()
                sentiment_score = market_sentiment.get('sentiment_score', 0)
                score += sentiment_score * 20
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return 50.0
    
    def _calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """Расчет анализа моментума (20% веса)"""
        try:
            score = 50.0
            
            # Price momentum (last 24h vs last week)
            recent_change = (df['close'].iloc[-1] / df['close'].iloc[-24] - 1) * 100
            weekly_change = (df['close'].iloc[-1] / df['close'].iloc[-168] - 1) * 100
            
            # Recent momentum
            if recent_change > 5:  # Strong positive momentum
                score += 20
            elif recent_change > 2:  # Moderate positive momentum
                score += 10
            elif recent_change < -5:  # Strong negative momentum
                score -= 20
            elif recent_change < -2:  # Moderate negative momentum
                score -= 10
            
            # Weekly trend consistency
            if (recent_change > 0 and weekly_change > 0) or (recent_change < 0 and weekly_change < 0):
                score += 10  # Consistent trend
            else:
                score -= 5  # Trend reversal
            
            # Volume momentum
            recent_volume = df['volume'].tail(24).mean()
            historical_volume = df['volume'].mean()
            
            volume_ratio = recent_volume / historical_volume
            if volume_ratio > 1.5:  # High volume activity
                score += 15
            elif volume_ratio < 0.5:  # Low volume
                score -= 10
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error in momentum analysis: {str(e)}")
            return 50.0
    
    def _interpret_analysis_score(self, total_score: float, technical: float, 
                                fundamental: float, sentiment: float, momentum: float) -> Tuple[str, float, str]:
        """Интерпретация общего анализа"""
        try:
            # Determine action based on total score
            if total_score >= 70:
                action = "BUY"
                confidence = min(total_score, 95)
            elif total_score <= 30:
                action = "SELL"
                confidence = min(100 - total_score, 95)
            else:
                action = "HOLD"
                confidence = 100 - abs(total_score - 50) * 2
            
            # Generate reasoning
            strongest_factor = max(
                ("технический", technical),
                ("фундаментальный", fundamental),
                ("настроения", sentiment),
                ("моментум", momentum),
                key=lambda x: x[1]
            )
            
            weakest_factor = min(
                ("технический", technical),
                ("фундаментальный", fundamental),
                ("настроения", sentiment),
                ("моментум", momentum),
                key=lambda x: x[1]
            )
            
            reasoning = f"Рекомендация {action} основана на общей оценке {total_score:.1f}/100. "
            reasoning += f"Сильнейший фактор: {strongest_factor[0]} анализ ({strongest_factor[1]:.1f}). "
            
            if action == "BUY":
                reasoning += "Положительные сигналы преобладают. "
            elif action == "SELL":
                reasoning += "Отрицательные сигналы преобладают. "
            else:
                reasoning += "Смешанные сигналы, рекомендуется ожидание. "
            
            reasoning += f"Слабейший фактор: {weakest_factor[0]} анализ ({weakest_factor[1]:.1f})."
            
            return action, confidence, reasoning
            
        except Exception as e:
            logger.error(f"Error interpreting analysis: {str(e)}")
            return "HOLD", 50.0, "Ошибка в анализе данных"
    
    def execute_trade(self, symbol: str, action: str, quantity: float, 
                     analysis: Dict = None) -> Dict:
        """Выполнение торговой операции"""
        try:
            if not analysis:
                analysis = self.analyze_symbol(symbol)
                if not analysis:
                    return {'success': False, 'error': 'Analysis failed'}
            
            # Check if confidence meets threshold
            if analysis['confidence'] < self.min_confidence_threshold:
                return {
                    'success': False,
                    'error': f"Confidence {analysis['confidence']:.1f}% below threshold {self.min_confidence_threshold}%"
                }
            
            # Check position limits
            current_positions = self.trading_history.get_current_positions()
            if len(current_positions) >= self.max_positions and action in ['BUY']:
                return {'success': False, 'error': 'Maximum positions reached'}
            
            # Get current price
            ticker = self.mexc_client.get_ticker_24hr(symbol)
            if not ticker or 'error' in ticker:
                return {'success': False, 'error': 'Unable to get current price'}
            
            current_price = float(ticker[0]['lastPrice']) if isinstance(ticker, list) else float(ticker['lastPrice'])
            
            # Execute order
            order_result = self.mexc_client.place_order(
                symbol=symbol,
                side=action,
                order_type='MARKET',
                quantity=quantity
            )
            
            if 'error' in order_result:
                log_trading_action(symbol, action, quantity, current_price, 
                                 analysis['reasoning'], success=False)
                return {'success': False, 'error': order_result['error']}
            
            # Record successful trade
            self.trading_history.add_trade(
                symbol=symbol,
                trade_type=action,
                quantity=quantity,
                price=current_price,
                analysis_data=analysis
            )
            
            # Send notification
            self.notifications.send_trade_notification(
                symbol=symbol,
                action=action,
                quantity=quantity,
                price=current_price,
                confidence=analysis['confidence']
            )
            
            log_trading_action(symbol, action, quantity, current_price, 
                             analysis['reasoning'], success=True)
            
            return {
                'success': True,
                'order_id': order_result.get('orderId'),
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': current_price,
                'confidence': analysis['confidence']
            }
            
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def auto_trade(self, symbols: List[str] = None, max_trades_per_session: int = 5) -> List[Dict]:
        """Автоматическая торговля"""
        try:
            if symbols is None:
                # Use popular USDT pairs
                symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT']
            
            executed_trades = []
            trades_count = 0
            
            # Update market conditions
            self.analyze_market_overview()
            
            for symbol in symbols:
                if trades_count >= max_trades_per_session:
                    break
                
                try:
                    # Analyze symbol
                    analysis = self.analyze_symbol(symbol)
                    
                    if not analysis or analysis['confidence'] < self.min_confidence_threshold:
                        continue
                    
                    # Determine position size
                    account_info = self.mexc_client.get_account_info()
                    if 'error' in account_info:
                        logger.warning("Unable to get account info for position sizing")
                        continue
                    
                    # Calculate position size (simplified)
                    usdt_balance = 0
                    for balance in account_info.get('balances', []):
                        if balance['asset'] == 'USDT':
                            usdt_balance = float(balance['free'])
                            break
                    
                    if usdt_balance < 50:  # Minimum trade size
                        continue
                    
                    position_value = usdt_balance * (self.position_size_pct / 100)
                    
                    # Get current price for quantity calculation
                    ticker = self.mexc_client.get_ticker_24hr(symbol)
                    if not ticker:
                        continue
                    
                    current_price = float(ticker[0]['lastPrice']) if isinstance(ticker, list) else float(ticker['lastPrice'])
                    quantity = position_value / current_price
                    
                    # Execute trade
                    if analysis['action'] in ['BUY', 'SELL']:
                        trade_result = self.execute_trade(symbol, analysis['action'], quantity, analysis)
                        
                        if trade_result['success']:
                            executed_trades.append(trade_result)
                            trades_count += 1
                            
                            # Wait between trades
                            time.sleep(2)
                
                except Exception as e:
                    logger.warning(f"Error in auto-trade for {symbol}: {str(e)}")
                    continue
            
            return executed_trades
            
        except Exception as e:
            logger.error(f"Error in auto-trade: {str(e)}")
            return []
    
    def update_ai_weights(self, trade_result: Dict, performance: float) -> None:
        """Обновление весов AI на основе производительности"""
        try:
            if performance > 0:  # Profitable trade
                adjustment = self.success_weight_adjustment
            else:  # Losing trade
                adjustment = self.failure_weight_adjustment
            
            # Get analysis data from trade
            analysis_data = trade_result.get('analysis_data', {})
            
            # Determine which factor contributed most to the decision
            scores = {
                'technical': analysis_data.get('technical_score', 50),
                'fundamental': analysis_data.get('fundamental_score', 50),
                'sentiment': analysis_data.get('sentiment_score', 50),
                'momentum': analysis_data.get('momentum_score', 50)
            }
            
            # Find the strongest factor
            strongest_factor = max(scores.items(), key=lambda x: x[1])[0]
            
            # Adjust weights
            old_weight = self.indicator_weights[strongest_factor]
            new_weight = max(0.1, min(0.6, old_weight + adjustment))
            self.indicator_weights[strongest_factor] = new_weight
            
            # Normalize weights
            total_weight = sum(self.indicator_weights.values())
            for key in self.indicator_weights:
                self.indicator_weights[key] /= total_weight
            
            logger.info(f"AI weights updated. Strongest factor: {strongest_factor}, "
                       f"Performance: {performance:.2f}%, New weights: {self.indicator_weights}")
            
        except Exception as e:
            logger.error(f"Error updating AI weights: {str(e)}")
