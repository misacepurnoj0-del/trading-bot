import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class TechnicalAnalysis:
    """Technical analysis calculations for trading signals"""
    
    def __init__(self):
        pass
    
    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return data.ewm(span=period).mean()
    
    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = self.calculate_ema(data, fast)
        ema_slow = self.calculate_ema(data, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(self, data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = self.calculate_sma(data, period)
        std = data.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=3).mean()
        
        return {
            'k': k_percent,
            'd': d_percent
        }
    
    def calculate_support_resistance(self, data: pd.DataFrame, window: int = 20) -> Dict[str, List[float]]:
        """Calculate support and resistance levels"""
        try:
            highs = data['high'].rolling(window=window).max()
            lows = data['low'].rolling(window=window).min()
            
            # Find local peaks and troughs
            resistance_levels = []
            support_levels = []
            
            for i in range(window, len(data) - window):
                # Check for resistance (local high)
                if data['high'].iloc[i] == highs.iloc[i]:
                    resistance_levels.append(data['high'].iloc[i])
                
                # Check for support (local low)
                if data['low'].iloc[i] == lows.iloc[i]:
                    support_levels.append(data['low'].iloc[i])
            
            # Remove duplicates and sort
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)[:5]
            support_levels = sorted(list(set(support_levels)))[:5]
            
            return {
                'resistance': resistance_levels,
                'support': support_levels
            }
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {str(e)}")
            return {'resistance': [], 'support': []}
    
    def analyze_trend(self, data: pd.DataFrame, short_period: int = 10, long_period: int = 20) -> Dict[str, any]:
        """Analyze price trend using moving averages"""
        try:
            close_prices = data['close']
            sma_short = self.calculate_sma(close_prices, short_period)
            sma_long = self.calculate_sma(close_prices, long_period)
            
            current_price = close_prices.iloc[-1]
            current_short_ma = sma_short.iloc[-1]
            current_long_ma = sma_long.iloc[-1]
            
            # Determine trend
            if current_short_ma > current_long_ma:
                trend = "Bullish"
            elif current_short_ma < current_long_ma:
                trend = "Bearish"
            else:
                trend = "Neutral"
            
            # Calculate trend strength
            ma_diff = abs(current_short_ma - current_long_ma) / current_price * 100
            
            if ma_diff > 5:
                strength = "Strong"
            elif ma_diff > 2:
                strength = "Moderate"
            else:
                strength = "Weak"
            
            return {
                'trend': trend,
                'strength': strength,
                'current_price': current_price,
                'short_ma': current_short_ma,
                'long_ma': current_long_ma,
                'ma_difference_pct': ma_diff
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trend: {str(e)}")
            return {
                'trend': 'Unknown',
                'strength': 'Unknown',
                'current_price': 0,
                'short_ma': 0,
                'long_ma': 0,
                'ma_difference_pct': 0
            }
    
    def get_comprehensive_analysis(self, data: pd.DataFrame) -> Dict[str, any]:
        """Get comprehensive technical analysis"""
        try:
            if len(data) < 50:
                logger.warning("Insufficient data for comprehensive analysis")
                return {}
            
            close_prices = data['close']
            high_prices = data['high']
            low_prices = data['low']
            
            # Calculate all indicators
            sma_10 = self.calculate_sma(close_prices, 10)
            sma_20 = self.calculate_sma(close_prices, 20)
            ema_12 = self.calculate_ema(close_prices, 12)
            rsi = self.calculate_rsi(close_prices)
            macd_data = self.calculate_macd(close_prices)
            bollinger = self.calculate_bollinger_bands(close_prices)
            stochastic = self.calculate_stochastic(high_prices, low_prices, close_prices)
            trend_analysis = self.analyze_trend(data)
            support_resistance = self.calculate_support_resistance(data)
            
            # Get latest values
            latest_data = {
                'price': float(close_prices.iloc[-1]),
                'sma_10': float(sma_10.iloc[-1]) if not pd.isna(sma_10.iloc[-1]) else 0,
                'sma_20': float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else 0,
                'ema_12': float(ema_12.iloc[-1]) if not pd.isna(ema_12.iloc[-1]) else 0,
                'rsi': float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50,
                'macd': float(macd_data['macd'].iloc[-1]) if not pd.isna(macd_data['macd'].iloc[-1]) else 0,
                'macd_signal': float(macd_data['signal'].iloc[-1]) if not pd.isna(macd_data['signal'].iloc[-1]) else 0,
                'bb_upper': float(bollinger['upper'].iloc[-1]) if not pd.isna(bollinger['upper'].iloc[-1]) else 0,
                'bb_lower': float(bollinger['lower'].iloc[-1]) if not pd.isna(bollinger['lower'].iloc[-1]) else 0,
                'stoch_k': float(stochastic['k'].iloc[-1]) if not pd.isna(stochastic['k'].iloc[-1]) else 50,
                'stoch_d': float(stochastic['d'].iloc[-1]) if not pd.isna(stochastic['d'].iloc[-1]) else 50,
                'trend': trend_analysis,
                'support_resistance': support_resistance
            }
            
            return latest_data
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {str(e)}")
            return {}
