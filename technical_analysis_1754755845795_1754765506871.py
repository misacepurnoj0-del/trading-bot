import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional, Union
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from utils.logger import get_logger

logger = get_logger(__name__)

class TechnicalAnalysis:
    """Comprehensive technical analysis engine for cryptocurrency trading"""
    
    def __init__(self):
        self.min_periods = {
            'sma': 5,
            'ema': 5, 
            'rsi': 14,
            'macd': 26,
            'bollinger': 20,
            'stochastic': 14
        }
        logger.info("Technical Analysis engine initialized")
    
    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        try:
            if len(data) < period:
                logger.warning(f"Insufficient data for SMA calculation: {len(data)} < {period}")
                return pd.Series(dtype=float, index=data.index)
            
            return data.rolling(window=period, min_periods=period).mean()
        except Exception as e:
            logger.error(f"Error calculating SMA: {str(e)}")
            return pd.Series(dtype=float, index=data.index)
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        try:
            if len(data) < period:
                logger.warning(f"Insufficient data for EMA calculation: {len(data)} < {period}")
                return pd.Series(dtype=float, index=data.index)
            
            return data.ewm(span=period, adjust=False).mean()
        except Exception as e:
            logger.error(f"Error calculating EMA: {str(e)}")
            return pd.Series(dtype=float, index=data.index)
    
    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index with enhanced accuracy"""
        try:
            if len(data) < period + 1:
                logger.warning(f"Insufficient data for RSI calculation: {len(data)} < {period + 1}")
                return pd.Series(dtype=float, index=data.index)
            
            delta = data.diff()
            
            # Separate gains and losses
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # Calculate the exponential moving average of gains and losses
            avg_gain = gain.ewm(span=period, adjust=False).mean()
            avg_loss = loss.ewm(span=period, adjust=False).mean()
            
            # Calculate relative strength
            rs = avg_gain / avg_loss
            
            # Calculate RSI
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            return pd.Series(dtype=float, index=data.index)
    
    def calculate_macd(self, data: pd.Series, fast: int = 12, slow: int = 26, 
                      signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence) with histogram"""
        try:
            if len(data) < slow + signal:
                logger.warning(f"Insufficient data for MACD calculation: {len(data)} < {slow + signal}")
                return {
                    'macd': pd.Series(dtype=float, index=data.index),
                    'signal': pd.Series(dtype=float, index=data.index),
                    'histogram': pd.Series(dtype=float, index=data.index)
                }
            
            # Calculate EMAs
            ema_fast = self.calculate_ema(data, fast)
            ema_slow = self.calculate_ema(data, slow)
            
            # Calculate MACD line
            macd_line = ema_fast - ema_slow
            
            # Calculate signal line
            signal_line = self.calculate_ema(macd_line, signal)
            
            # Calculate histogram
            histogram = macd_line - signal_line
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            return {
                'macd': pd.Series(dtype=float),
                'signal': pd.Series(dtype=float),
                'histogram': pd.Series(dtype=float)
            }
    
    def calculate_bollinger_bands(self, data: pd.Series, period: int = 20, 
                                 std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands with additional metrics"""
        try:
            if len(data) < period:
                logger.warning(f"Insufficient data for Bollinger Bands: {len(data)} < {period}")
                return {
                    'upper': pd.Series(dtype=float, index=data.index),
                    'middle': pd.Series(dtype=float, index=data.index),
                    'lower': pd.Series(dtype=float, index=data.index),
                    'bandwidth': pd.Series(dtype=float, index=data.index),
                    'percent_b': pd.Series(dtype=float, index=data.index)
                }
            
            # Calculate middle band (SMA)
            sma = self.calculate_sma(data, period)
            
            # Calculate standard deviation
            std = data.rolling(window=period, min_periods=period).std()
            
            # Calculate bands
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            
            # Calculate additional metrics
            bandwidth = ((upper_band - lower_band) / sma) * 100
            percent_b = (data - lower_band) / (upper_band - lower_band)
            
            return {
                'upper': upper_band,
                'middle': sma,
                'lower': lower_band,
                'bandwidth': bandwidth,
                'percent_b': percent_b
            }
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {str(e)}")
            return {
                'upper': pd.Series(dtype=float),
                'middle': pd.Series(dtype=float),
                'lower': pd.Series(dtype=float),
                'bandwidth': pd.Series(dtype=float),
                'percent_b': pd.Series(dtype=float)
            }
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        try:
            if len(close) < k_period:
                logger.warning(f"Insufficient data for Stochastic: {len(close)} < {k_period}")
                return {
                    'k': pd.Series(dtype=float, index=close.index),
                    'd': pd.Series(dtype=float, index=close.index)
                }
            
            # Calculate %K
            lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
            highest_high = high.rolling(window=k_period, min_periods=k_period).max()
            
            k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            
            # Calculate %D (smoothed %K)
            d_percent = k_percent.rolling(window=d_period, min_periods=d_period).mean()
            
            return {
                'k': k_percent,
                'd': d_percent
            }
        except Exception as e:
            logger.error(f"Error calculating Stochastic: {str(e)}")
            return {
                'k': pd.Series(dtype=float),
                'd': pd.Series(dtype=float)
            }
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                     period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        try:
            if len(close) < period + 1:
                logger.warning(f"Insufficient data for ATR: {len(close)} < {period + 1}")
                return pd.Series(dtype=float, index=close.index)
            
            # Calculate True Range components
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            # True Range is the maximum of the three
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate ATR using exponential moving average
            atr = tr.ewm(span=period, adjust=False).mean()
            
            return atr
        except Exception as e:
            logger.error(f"Error calculating ATR: {str(e)}")
            return pd.Series(dtype=float, index=close.index)
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = 14) -> Dict[str, pd.Series]:
        """Calculate Average Directional Index (ADX) and Directional Indicators"""
        try:
            if len(close) < period * 2:
                logger.warning(f"Insufficient data for ADX: {len(close)} < {period * 2}")
                return {
                    'adx': pd.Series(dtype=float, index=close.index),
                    'plus_di': pd.Series(dtype=float, index=close.index),
                    'minus_di': pd.Series(dtype=float, index=close.index)
                }
            
            # Calculate True Range
            atr = self.calculate_atr(high, low, close, period)
            
            # Calculate Directional Movement
            high_diff = high.diff()
            low_diff = -low.diff()
            
            plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
            minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
            
            # Smooth the DM values
            plus_dm_smooth = plus_dm.ewm(span=period, adjust=False).mean()
            minus_dm_smooth = minus_dm.ewm(span=period, adjust=False).mean()
            
            # Calculate DI values
            plus_di = 100 * (plus_dm_smooth / atr)
            minus_di = 100 * (minus_dm_smooth / atr)
            
            # Calculate DX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            dx = dx.replace([np.inf, -np.inf], 0)  # Handle division by zero
            
            # Calculate ADX
            adx = dx.ewm(span=period, adjust=False).mean()
            
            return {
                'adx': adx,
                'plus_di': plus_di,
                'minus_di': minus_di
            }
        except Exception as e:
            logger.error(f"Error calculating ADX: {str(e)}")
            return {
                'adx': pd.Series(dtype=float),
                'plus_di': pd.Series(dtype=float),
                'minus_di': pd.Series(dtype=float)
            }
    
    def calculate_support_resistance(self, data: pd.DataFrame, window: int = 20, 
                                   min_touches: int = 2) -> Dict[str, List[float]]:
        """Calculate dynamic support and resistance levels"""
        try:
            if len(data) < window * 2:
                logger.warning(f"Insufficient data for support/resistance: {len(data)} < {window * 2}")
                return {'resistance': [], 'support': []}
            
            highs = data['high'].rolling(window=window, center=True).max()
            lows = data['low'].rolling(window=window, center=True).min()
            
            # Find local peaks and troughs
            resistance_levels = []
            support_levels = []
            
            # Identify local highs (resistance)
            for i in range(window, len(data) - window):
                if (data['high'].iloc[i] == highs.iloc[i] and 
                    data['high'].iloc[i] > data['high'].iloc[i-1] and 
                    data['high'].iloc[i] > data['high'].iloc[i+1]):
                    
                    resistance_levels.append(data['high'].iloc[i])
            
            # Identify local lows (support)
            for i in range(window, len(data) - window):
                if (data['low'].iloc[i] == lows.iloc[i] and
                    data['low'].iloc[i] < data['low'].iloc[i-1] and
                    data['low'].iloc[i] < data['low'].iloc[i+1]):
                    
                    support_levels.append(data['low'].iloc[i])
            
            # Cluster similar levels
            resistance_levels = self._cluster_levels(resistance_levels, min_touches)
            support_levels = self._cluster_levels(support_levels, min_touches)
            
            # Sort and limit results
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)[:10]
            support_levels = sorted(list(set(support_levels)))[:10]
            
            return {
                'resistance': resistance_levels,
                'support': support_levels
            }
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {str(e)}")
            return {'resistance': [], 'support': []}
    
    def _cluster_levels(self, levels: List[float], min_touches: int, 
                       tolerance: float = 0.02) -> List[float]:
        """Cluster similar price levels"""
        if not levels:
            return []
        
        clustered = []
        sorted_levels = sorted(levels)
        
        i = 0
        while i < len(sorted_levels):
            cluster = [sorted_levels[i]]
            j = i + 1
            
            # Find all levels within tolerance
            while j < len(sorted_levels):
                if abs(sorted_levels[j] - sorted_levels[i]) / sorted_levels[i] <= tolerance:
                    cluster.append(sorted_levels[j])
                    j += 1
                else:
                    break
            
            # Only include clusters with minimum touches
            if len(cluster) >= min_touches:
                clustered.append(np.mean(cluster))
            
            i = j
        
        return clustered
    
    def analyze_trend(self, data: pd.DataFrame, short_period: int = 10, 
                     long_period: int = 20) -> Dict[str, Union[str, float]]:
        """Comprehensive trend analysis using multiple indicators"""
        try:
            if len(data) < long_period:
                logger.warning(f"Insufficient data for trend analysis: {len(data)} < {long_period}")
                return {
                    'trend': 'Unknown',
                    'strength': 'Unknown', 
                    'confidence': 0.0,
                    'current_price': 0,
                    'short_ma': 0,
                    'long_ma': 0,
                    'ma_difference_pct': 0
                }
            
            close_prices = data['close']
            current_price = close_prices.iloc[-1]
            
            # Calculate moving averages
            sma_short = self.calculate_sma(close_prices, short_period)
            sma_long = self.calculate_sma(close_prices, long_period)
            ema_short = self.calculate_ema(close_prices, short_period)
            
            current_short_ma = sma_short.iloc[-1] if not pd.isna(sma_short.iloc[-1]) else current_price
            current_long_ma = sma_long.iloc[-1] if not pd.isna(sma_long.iloc[-1]) else current_price
            current_ema = ema_short.iloc[-1] if not pd.isna(ema_short.iloc[-1]) else current_price
            
            # Trend direction analysis
            trend_signals = []
            
            # MA crossover
            if current_short_ma > current_long_ma:
                trend_signals.append(1)
            else:
                trend_signals.append(-1)
            
            # Price vs EMA
            if current_price > current_ema:
                trend_signals.append(1)
            else:
                trend_signals.append(-1)
            
            # Price momentum (last 5 periods)
            if len(close_prices) >= 5:
                recent_momentum = (current_price - close_prices.iloc[-5]) / close_prices.iloc[-5]
                if recent_momentum > 0.01:  # 1% threshold
                    trend_signals.append(1)
                elif recent_momentum < -0.01:
                    trend_signals.append(-1)
                else:
                    trend_signals.append(0)
            
            # Calculate ADX for trend strength
            adx_data = self.calculate_adx(data['high'], data['low'], data['close'])
            current_adx = adx_data['adx'].iloc[-1] if not pd.isna(adx_data['adx'].iloc[-1]) else 0
            
            # Determine overall trend
            trend_score = sum(trend_signals)
            
            if trend_score >= 2:
                trend = "Bullish"
            elif trend_score <= -2:
                trend = "Bearish"
            else:
                trend = "Neutral"
            
            # Calculate trend strength
            ma_diff = abs(current_short_ma - current_long_ma) / current_price * 100
            
            if current_adx > 30 and ma_diff > 5:
                strength = "Very Strong"
                confidence = 0.9
            elif current_adx > 25 or ma_diff > 3:
                strength = "Strong"
                confidence = 0.7
            elif current_adx > 20 or ma_diff > 2:
                strength = "Moderate"
                confidence = 0.5
            else:
                strength = "Weak"
                confidence = 0.3
            
            return {
                'trend': trend,
                'strength': strength,
                'confidence': confidence,
                'current_price': current_price,
                'short_ma': current_short_ma,
                'long_ma': current_long_ma,
                'ma_difference_pct': ma_diff,
                'adx': current_adx,
                'trend_score': trend_score
            }
        except Exception as e:
            logger.error(f"Error analyzing trend: {str(e)}")
            return {
                'trend': 'Error',
                'strength': 'Unknown',
                'confidence': 0.0,
                'current_price': 0,
                'short_ma': 0,
                'long_ma': 0,
                'ma_difference_pct': 0
            }
    
    def calculate_fibonacci_retracement(self, data: pd.Series, period: int = 50) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        try:
            if len(data) < period:
                return {}
            
            recent_data = data.tail(period)
            high_price = recent_data.max()
            low_price = recent_data.min()
            
            diff = high_price - low_price
            
            levels = {
                '0.0%': high_price,
                '23.6%': high_price - 0.236 * diff,
                '38.2%': high_price - 0.382 * diff,
                '50.0%': high_price - 0.5 * diff,
                '61.8%': high_price - 0.618 * diff,
                '78.6%': high_price - 0.786 * diff,
                '100.0%': low_price,
                '161.8%': low_price - 0.618 * diff,  # Extension
                '261.8%': low_price - 1.618 * diff   # Extension
            }
            
            return levels
        except Exception as e:
            logger.error(f"Error calculating Fibonacci retracement: {str(e)}")
            return {}
    
    def get_comprehensive_analysis(self, data: pd.DataFrame) -> Dict[str, any]:
        """Get comprehensive technical analysis with all indicators"""
        try:
            if len(data) < 50:
                logger.warning("Insufficient data for comprehensive analysis")
                return {'error': 'Insufficient data'}
            
            close_prices = data['close']
            high_prices = data['high']
            low_prices = data['low']
            
            analysis_results = {}
            
            # Basic moving averages
            analysis_results['sma_10'] = float(self.calculate_sma(close_prices, 10).iloc[-1])
            analysis_results['sma_20'] = float(self.calculate_sma(close_prices, 20).iloc[-1])
            analysis_results['sma_50'] = float(self.calculate_sma(close_prices, 50).iloc[-1])
            analysis_results['ema_12'] = float(self.calculate_ema(close_prices, 12).iloc[-1])
            analysis_results['ema_26'] = float(self.calculate_ema(close_prices, 26).iloc[-1])
            
            # Oscillators
            rsi = self.calculate_rsi(close_prices)
            analysis_results['rsi'] = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
            
            macd_data = self.calculate_macd(close_prices)
            analysis_results['macd'] = float(macd_data['macd'].iloc[-1]) if not pd.isna(macd_data['macd'].iloc[-1]) else 0
            analysis_results['macd_signal'] = float(macd_data['signal'].iloc[-1]) if not pd.isna(macd_data['signal'].iloc[-1]) else 0
            analysis_results['macd_histogram'] = float(macd_data['histogram'].iloc[-1]) if not pd.isna(macd_data['histogram'].iloc[-1]) else 0
            
            # Bollinger Bands
            bollinger = self.calculate_bollinger_bands(close_prices)
            analysis_results['bb_upper'] = float(bollinger['upper'].iloc[-1]) if not pd.isna(bollinger['upper'].iloc[-1]) else 0
            analysis_results['bb_middle'] = float(bollinger['middle'].iloc[-1]) if not pd.isna(bollinger['middle'].iloc[-1]) else 0
            analysis_results['bb_lower'] = float(bollinger['lower'].iloc[-1]) if not pd.isna(bollinger['lower'].iloc[-1]) else 0
            analysis_results['bb_percent_b'] = float(bollinger['percent_b'].iloc[-1]) if not pd.isna(bollinger['percent_b'].iloc[-1]) else 0
            
            # Stochastic
            stochastic = self.calculate_stochastic(high_prices, low_prices, close_prices)
            analysis_results['stoch_k'] = float(stochastic['k'].iloc[-1]) if not pd.isna(stochastic['k'].iloc[-1]) else 50
            analysis_results['stoch_d'] = float(stochastic['d'].iloc[-1]) if not pd.isna(stochastic['d'].iloc[-1]) else 50
            
            # ATR
            atr = self.calculate_atr(high_prices, low_prices, close_prices)
            analysis_results['atr'] = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0
            
            # ADX
            adx_data = self.calculate_adx(high_prices, low_prices, close_prices)
            analysis_results['adx'] = float(adx_data['adx'].iloc[-1]) if not pd.isna(adx_data['adx'].iloc[-1]) else 0
            analysis_results['plus_di'] = float(adx_data['plus_di'].iloc[-1]) if not pd.isna(adx_data['plus_di'].iloc[-1]) else 0
            analysis_results['minus_di'] = float(adx_data['minus_di'].iloc[-1]) if not pd.isna(adx_data['minus_di'].iloc[-1]) else 0
            
            # Trend analysis
            trend_analysis = self.analyze_trend(data)
            analysis_results['trend'] = trend_analysis
            
            # Support and resistance
            support_resistance = self.calculate_support_resistance(data)
            analysis_results['support_resistance'] = support_resistance
            
            # Fibonacci levels
            fibonacci = self.calculate_fibonacci_retracement(close_prices)
            analysis_results['fibonacci'] = fibonacci
            
            # Current price info
            analysis_results['current_price'] = float(close_prices.iloc[-1])
            analysis_results['volume'] = float(data['volume'].iloc[-1]) if 'volume' in data.columns else 0
            
            # Generate trading signals
            analysis_results['signals'] = self._generate_trading_signals(analysis_results)
            
            # Calculate overall score
            analysis_results['technical_score'] = self._calculate_technical_score(analysis_results)
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {str(e)}")
            return {'error': str(e)}
    
    def _generate_trading_signals(self, analysis: Dict) -> Dict[str, str]:
        """Generate trading signals based on technical analysis"""
        signals = {
            'rsi_signal': 'NEUTRAL',
            'macd_signal': 'NEUTRAL', 
            'bb_signal': 'NEUTRAL',
            'trend_signal': 'NEUTRAL',
            'overall_signal': 'NEUTRAL'
        }
        
        try:
            # RSI signals
            rsi = analysis.get('rsi', 50)
            if rsi > 70:
                signals['rsi_signal'] = 'SELL'
            elif rsi < 30:
                signals['rsi_signal'] = 'BUY'
            
            # MACD signals
            macd = analysis.get('macd', 0)
            macd_signal = analysis.get('macd_signal', 0)
            if macd > macd_signal and analysis.get('macd_histogram', 0) > 0:
                signals['macd_signal'] = 'BUY'
            elif macd < macd_signal and analysis.get('macd_histogram', 0) < 0:
                signals['macd_signal'] = 'SELL'
            
            # Bollinger Bands signals
            bb_percent_b = analysis.get('bb_percent_b', 0.5)
            if bb_percent_b > 0.8:
                signals['bb_signal'] = 'SELL'
            elif bb_percent_b < 0.2:
                signals['bb_signal'] = 'BUY'
            
            # Trend signals
            trend_info = analysis.get('trend', {})
            if isinstance(trend_info, dict):
                trend = trend_info.get('trend', 'Neutral')
                if trend == 'Bullish':
                    signals['trend_signal'] = 'BUY'
                elif trend == 'Bearish':
                    signals['trend_signal'] = 'SELL'
            
            # Overall signal (majority vote)
            buy_votes = sum(1 for signal in signals.values() if signal == 'BUY')
            sell_votes = sum(1 for signal in signals.values() if signal == 'SELL')
            
            if buy_votes > sell_votes:
                signals['overall_signal'] = 'BUY'
            elif sell_votes > buy_votes:
                signals['overall_signal'] = 'SELL'
            
        except Exception as e:
            logger.error(f"Error generating trading signals: {str(e)}")
        
        return signals
    
    def _calculate_technical_score(self, analysis: Dict) -> float:
        """Calculate overall technical score (0-100)"""
        try:
            score = 50.0  # Neutral starting point
            
            # RSI contribution
            rsi = analysis.get('rsi', 50)
            if 30 <= rsi <= 70:
                score += 10  # Good RSI range
            elif rsi > 80 or rsi < 20:
                score -= 10  # Extreme RSI
            
            # Trend contribution
            trend_info = analysis.get('trend', {})
            if isinstance(trend_info, dict):
                confidence = trend_info.get('confidence', 0)
                if trend_info.get('trend') == 'Bullish':
                    score += confidence * 20
                elif trend_info.get('trend') == 'Bearish':
                    score -= confidence * 20
            
            # MACD contribution
            macd_histogram = analysis.get('macd_histogram', 0)
            if macd_histogram > 0:
                score += 5
            elif macd_histogram < 0:
                score -= 5
            
            # ADX contribution (trend strength)
            adx = analysis.get('adx', 0)
            if adx > 25:
                score += 10  # Strong trend
            elif adx < 20:
                score -= 5   # Weak trend
            
            # Ensure score is within bounds
            score = max(0, min(100, score))
            
            return round(score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating technical score: {str(e)}")
            return 50.0
