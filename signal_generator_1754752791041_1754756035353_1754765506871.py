import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time

from utils.logger import get_logger, log_trading_action
from analysis.technical_analysis import TechnicalAnalysis
from analysis.indicators import TechnicalIndicators
from news.news_parser import NewsParser

logger = get_logger(__name__)

class SignalGenerator:
    """Advanced signal generation system with AI-enhanced analysis"""
    
    def __init__(self):
        self.technical_analysis = TechnicalAnalysis()
        self.indicators = TechnicalIndicators()
        self.news_parser = NewsParser()
        
        # Signal generation parameters
        self.min_confidence_threshold = 65.0
        self.signal_weights = {
            'technical_indicators': 0.4,
            'price_action': 0.25,
            'volume_analysis': 0.15,
            'sentiment': 0.20
        }
        
        # Signal strength thresholds
        self.strong_signal_threshold = 80.0
        self.weak_signal_threshold = 55.0
        
        # Cache for signal analysis
        self.signal_cache = {}
        self.cache_duration = 180  # 3 minutes
        
        logger.info("Signal Generator initialized")
    
    def generate_trading_signal(self, symbol: str, market_data: pd.DataFrame) -> Optional[Dict]:
        """Generate comprehensive trading signal for a symbol"""
        try:
            if len(market_data) < 50:
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Check cache first
            cache_key = f"signal_{symbol}"
            if cache_key in self.signal_cache:
                cached_signal = self.signal_cache[cache_key]
                if time.time() - cached_signal['timestamp'] < self.cache_duration:
                    return cached_signal['signal']
            
            # Generate multi-faceted analysis
            technical_score = self._analyze_technical_indicators(market_data)
            price_action_score = self._analyze_price_action(market_data)
            volume_score = self._analyze_volume_patterns(market_data)
            sentiment_score = self._analyze_market_sentiment(symbol)
            
            # Calculate weighted final score
            final_score = (
                technical_score * self.signal_weights['technical_indicators'] +
                price_action_score * self.signal_weights['price_action'] +
                volume_score * self.signal_weights['volume_analysis'] +
                sentiment_score * self.signal_weights['sentiment']
            )
            
            # Determine signal strength and action
            signal = self._interpret_signal(final_score, technical_score, price_action_score, volume_score, sentiment_score)
            
            # Add symbol and timestamp
            signal['symbol'] = symbol
            signal['timestamp'] = datetime.now()
            signal['components'] = {
                'technical_score': technical_score,
                'price_action_score': price_action_score,
                'volume_score': volume_score,
                'sentiment_score': sentiment_score
            }
            
            # Cache the signal
            self.signal_cache[cache_key] = {
                'signal': signal,
                'timestamp': time.time()
            }
            
            log_trading_action("SIGNAL_GENERATED", symbol, {
                'action': signal['action'],
                'confidence': signal['confidence'],
                'final_score': final_score
            })
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {str(e)}")
            return None
    
    def _analyze_technical_indicators(self, data: pd.DataFrame) -> float:
        """Analyze technical indicators and return score (0-100)"""
        try:
            # Get comprehensive technical analysis
            tech_analysis = self.technical_analysis.get_comprehensive_analysis(data)
            
            if not tech_analysis:
                return 50.0  # Neutral
            
            score = 50.0  # Base score
            
            # RSI analysis
            rsi = tech_analysis.get('rsi', 50)
            if rsi < 30:  # Oversold - bullish
                score += 15
            elif rsi > 70:  # Overbought - bearish
                score -= 15
            elif 40 <= rsi <= 60:  # Neutral zone
                score += 5
            
            # MACD analysis
            macd = tech_analysis.get('macd', 0)
            macd_signal = tech_analysis.get('macd_signal', 0)
            if macd > macd_signal and macd > 0:  # Bullish momentum
                score += 12
            elif macd < macd_signal and macd < 0:  # Bearish momentum
                score -= 12
            
            # Moving averages
            price = tech_analysis.get('price', 0)
            sma_10 = tech_analysis.get('sma_10', 0)
            sma_20 = tech_analysis.get('sma_20', 0)
            
            if price > sma_10 > sma_20:  # Strong uptrend
                score += 15
            elif price < sma_10 < sma_20:  # Strong downtrend
                score -= 15
            elif price > sma_20:  # Above long-term average
                score += 8
            elif price < sma_20:  # Below long-term average
                score -= 8
            
            # Bollinger Bands
            bb_upper = tech_analysis.get('bb_upper', 0)
            bb_lower = tech_analysis.get('bb_lower', 0)
            
            if price < bb_lower:  # Oversold
                score += 10
            elif price > bb_upper:  # Overbought
                score -= 10
            
            # Stochastic
            stoch_k = tech_analysis.get('stoch_k', 50)
            stoch_d = tech_analysis.get('stoch_d', 50)
            
            if stoch_k < 20 and stoch_d < 20:  # Oversold
                score += 8
            elif stoch_k > 80 and stoch_d > 80:  # Overbought
                score -= 8
            elif stoch_k > stoch_d and stoch_k < 80:  # Bullish crossover
                score += 5
            elif stoch_k < stoch_d and stoch_k > 20:  # Bearish crossover
                score -= 5
            
            # Get advanced indicators
            indicators_data = self.indicators.get_all_indicators(data)
            if indicators_data.get('analysis_complete'):
                latest_values = indicators_data['latest_values']
                
                # Williams %R
                williams_r = latest_values.get('williams_r', 0)
                if williams_r < -80:
                    score += 6
                elif williams_r > -20:
                    score -= 6
                
                # CCI
                cci = latest_values.get('cci', 0)
                if cci < -100:
                    score += 6
                elif cci > 100:
                    score -= 6
                
                # MFI
                mfi = latest_values.get('mfi', 50)
                if mfi < 20:
                    score += 6
                elif mfi > 80:
                    score -= 6
                
                # Parabolic SAR
                current_price = latest_values.get('current_price', 0)
                sar = latest_values.get('parabolic_sar', 0)
                if current_price > sar:
                    score += 5
                elif current_price < sar:
                    score -= 5
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {str(e)}")
            return 50.0
    
    def _analyze_price_action(self, data: pd.DataFrame) -> float:
        """Analyze price action patterns and return score (0-100)"""
        try:
            score = 50.0
            
            # Get recent price data
            close_prices = data['close']
            high_prices = data['high']
            low_prices = data['low']
            
            # Trend analysis
            trend_data = self.technical_analysis.analyze_trend(data)
            
            if trend_data['trend'] == 'Bullish':
                if trend_data['strength'] == 'Strong':
                    score += 20
                elif trend_data['strength'] == 'Moderate':
                    score += 12
                else:
                    score += 5
            elif trend_data['trend'] == 'Bearish':
                if trend_data['strength'] == 'Strong':
                    score -= 20
                elif trend_data['strength'] == 'Moderate':
                    score -= 12
                else:
                    score -= 5
            
            # Support and resistance analysis
            support_resistance = self.technical_analysis.calculate_support_resistance(data)
            current_price = close_prices.iloc[-1]
            
            # Check proximity to support/resistance
            if support_resistance['support']:
                nearest_support = max([s for s in support_resistance['support'] if s < current_price], default=0)
                if nearest_support > 0:
                    support_distance = ((current_price - nearest_support) / current_price) * 100
                    if support_distance < 2:  # Very close to support
                        score += 10
                    elif support_distance < 5:  # Near support
                        score += 5
            
            if support_resistance['resistance']:
                nearest_resistance = min([r for r in support_resistance['resistance'] if r > current_price], default=float('inf'))
                if nearest_resistance != float('inf'):
                    resistance_distance = ((nearest_resistance - current_price) / current_price) * 100
                    if resistance_distance < 2:  # Very close to resistance
                        score -= 10
                    elif resistance_distance < 5:  # Near resistance
                        score -= 5
            
            # Momentum analysis
            recent_returns = close_prices.pct_change().tail(10)
            momentum = recent_returns.mean() * 100
            
            if momentum > 2:  # Strong positive momentum
                score += 15
            elif momentum > 0.5:  # Moderate positive momentum
                score += 8
            elif momentum < -2:  # Strong negative momentum
                score -= 15
            elif momentum < -0.5:  # Moderate negative momentum
                score -= 8
            
            # Volatility analysis
            volatility = recent_returns.std() * 100
            if 1 < volatility < 5:  # Moderate volatility is good for trading
                score += 5
            elif volatility > 10:  # High volatility - risky
                score -= 5
            
            # Candlestick patterns (simplified)
            last_candle = {
                'open': data['open'].iloc[-1],
                'high': data['high'].iloc[-1],
                'low': data['low'].iloc[-1],
                'close': data['close'].iloc[-1]
            }
            
            prev_candle = {
                'open': data['open'].iloc[-2],
                'high': data['high'].iloc[-2],
                'low': data['low'].iloc[-2],
                'close': data['close'].iloc[-2]
            }
            
            # Doji pattern
            body_size = abs(last_candle['close'] - last_candle['open'])
            candle_range = last_candle['high'] - last_candle['low']
            if body_size < candle_range * 0.1:  # Doji
                score -= 2  # Indecision
            
            # Hammer pattern
            lower_shadow = last_candle['open'] - last_candle['low'] if last_candle['close'] > last_candle['open'] else last_candle['close'] - last_candle['low']
            if lower_shadow > body_size * 2 and lower_shadow > candle_range * 0.6:
                score += 8  # Potential reversal
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error in price action analysis: {str(e)}")
            return 50.0
    
    def _analyze_volume_patterns(self, data: pd.DataFrame) -> float:
        """Analyze volume patterns and return score (0-100)"""
        try:
            score = 50.0
            
            if 'volume' not in data.columns:
                return score  # No volume data available
            
            volume = data['volume']
            close_prices = data['close']
            
            # Volume trend analysis
            recent_volume = volume.tail(10).mean()
            historical_volume = volume.tail(30).mean()
            
            volume_ratio = recent_volume / historical_volume if historical_volume > 0 else 1
            
            if volume_ratio > 1.5:  # High volume
                # Check if high volume accompanies price movement
                recent_price_change = (close_prices.iloc[-1] - close_prices.iloc[-10]) / close_prices.iloc[-10]
                if recent_price_change > 0.02:  # Positive price change with high volume
                    score += 15
                elif recent_price_change < -0.02:  # Negative price change with high volume
                    score -= 10
                else:
                    score += 5  # High volume but no clear direction
            elif volume_ratio < 0.7:  # Low volume
                score -= 8  # Lack of conviction
            
            # Volume and price divergence
            price_changes = close_prices.pct_change().tail(10)
            volume_changes = volume.pct_change().tail(10)
            
            # Calculate correlation between price and volume changes
            try:
                correlation = np.corrcoef(price_changes.dropna(), volume_changes.dropna())[0, 1]
                if not np.isnan(correlation):
                    if correlation > 0.3:  # Positive correlation - healthy
                        score += 8
                    elif correlation < -0.3:  # Negative correlation - divergence
                        score -= 5
            except:
                pass
            
            # On-Balance Volume analysis
            obv_data = self.indicators.on_balance_volume(close_prices, volume)
            if len(obv_data) > 10:
                obv_trend = (obv_data.iloc[-1] - obv_data.iloc[-10]) / abs(obv_data.iloc[-10]) if obv_data.iloc[-10] != 0 else 0
                price_trend = (close_prices.iloc[-1] - close_prices.iloc[-10]) / close_prices.iloc[-10]
                
                # Check for OBV and price convergence
                if (obv_trend > 0 and price_trend > 0) or (obv_trend < 0 and price_trend < 0):
                    score += 10  # Convergence
                elif abs(obv_trend - price_trend) > 0.1:
                    score -= 8  # Divergence
            
            # Volume spike analysis
            volume_spikes = volume.tail(5) > (volume.tail(20).mean() * 2)
            recent_spikes = volume_spikes.sum()
            
            if recent_spikes >= 2:  # Multiple volume spikes
                recent_price_trend = (close_prices.iloc[-1] - close_prices.iloc[-5]) / close_prices.iloc[-5]
                if recent_price_trend > 0:
                    score += 12  # Volume confirming uptrend
                else:
                    score -= 8  # Volume confirming downtrend
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error in volume analysis: {str(e)}")
            return 50.0
    
    def _analyze_market_sentiment(self, symbol: str) -> float:
        """Analyze market sentiment and return score (0-100)"""
        try:
            score = 50.0  # Base neutral score
            
            # Get general market sentiment
            market_sentiment = self.news_parser.get_market_sentiment()
            
            if market_sentiment['overall_sentiment'] == 'Bullish':
                score += 15 * market_sentiment['confidence']
            elif market_sentiment['overall_sentiment'] == 'Bearish':
                score -= 15 * market_sentiment['confidence']
            
            # Get symbol-specific sentiment
            symbol_sentiment = self.news_parser.analyze_symbol_sentiment(symbol)
            
            if symbol_sentiment:
                sentiment_score = symbol_sentiment['sentiment_score']
                confidence = symbol_sentiment['confidence']
                
                # Symbol-specific sentiment has higher weight
                score += (sentiment_score * 100 * confidence * 0.3)
            
            # Adjust based on news volume
            if market_sentiment['articles_analyzed'] > 20:
                # High news volume - increase confidence in sentiment
                if market_sentiment['overall_sentiment'] != 'Neutral':
                    adjustment = 5 if market_sentiment['overall_sentiment'] == 'Bullish' else -5
                    score += adjustment
            elif market_sentiment['articles_analyzed'] < 5:
                # Low news volume - reduce confidence
                score = score * 0.9 + 50 * 0.1  # Move towards neutral
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return 50.0
    
    def _interpret_signal(self, final_score: float, technical_score: float, 
                         price_action_score: float, volume_score: float, sentiment_score: float) -> Dict:
        """Interpret the final score and generate trading signal"""
        try:
            # Determine action based on final score
            if final_score >= 65:
                action = "BUY"
                confidence = final_score
            elif final_score <= 35:
                action = "SELL"
                confidence = 100 - final_score
            else:
                action = "HOLD"
                confidence = 50
            
            # Adjust confidence based on score consistency
            scores = [technical_score, price_action_score, volume_score, sentiment_score]
            score_std = np.std(scores)
            
            if score_std > 25:  # High variance - reduce confidence
                confidence *= 0.8
            elif score_std < 15:  # Low variance - increase confidence
                confidence *= 1.1
            
            # Determine signal strength
            if confidence >= self.strong_signal_threshold:
                strength = "Strong"
            elif confidence >= self.weak_signal_threshold:
                strength = "Moderate"
            else:
                strength = "Weak"
            
            # Generate reasoning
            reasoning_parts = []
            
            if technical_score > 60:
                reasoning_parts.append("Технические индикаторы показывают бычий сигнал")
            elif technical_score < 40:
                reasoning_parts.append("Технические индикаторы показывают медвежий сигнал")
            
            if price_action_score > 60:
                reasoning_parts.append("Ценовое действие поддерживает рост")
            elif price_action_score < 40:
                reasoning_parts.append("Ценовое действие указывает на снижение")
            
            if volume_score > 60:
                reasoning_parts.append("Объемы подтверждают движение")
            elif volume_score < 40:
                reasoning_parts.append("Слабые объемы не поддерживают движение")
            
            if sentiment_score > 60:
                reasoning_parts.append("Позитивные новости и настроения")
            elif sentiment_score < 40:
                reasoning_parts.append("Негативные новости влияют на настроения")
            
            reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Смешанные сигналы от различных индикаторов"
            
            # Final confidence adjustment
            confidence = max(0, min(95, confidence))
            
            return {
                'action': action,
                'confidence': confidence,
                'strength': strength,
                'final_score': final_score,
                'reasoning': reasoning,
                'risk_level': 'Low' if confidence >= 80 else 'Medium' if confidence >= 60 else 'High'
            }
            
        except Exception as e:
            logger.error(f"Error interpreting signal: {str(e)}")
            return {
                'action': 'HOLD',
                'confidence': 50,
                'strength': 'Weak',
                'final_score': 50,
                'reasoning': 'Ошибка анализа сигнала',
                'risk_level': 'High'
            }
    
    def batch_generate_signals(self, symbols_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """Generate signals for multiple symbols"""
        signals = []
        
        for symbol, data in symbols_data.items():
            try:
                signal = self.generate_trading_signal(symbol, data)
                if signal and signal['confidence'] >= self.min_confidence_threshold:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error generating signal for {symbol}: {str(e)}")
                continue
        
        # Sort by confidence
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        return signals
    
    def clear_cache(self):
        """Clear the signal cache"""
        self.signal_cache.clear()
        logger.info("Signal cache cleared")
    
    def get_signal_statistics(self) -> Dict:
        """Get statistics about signal generation"""
        return {
            'cache_size': len(self.signal_cache),
            'min_confidence_threshold': self.min_confidence_threshold,
            'strong_signal_threshold': self.strong_signal_threshold,
            'signal_weights': self.signal_weights
        }
