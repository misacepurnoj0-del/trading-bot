import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import talib

from utils.logger import get_logger, log_error

logger = get_logger(__name__)

class TechnicalAnalysis:
    """Класс для технического анализа"""
    
    def __init__(self):
        self.indicators = {}
        
    def get_comprehensive_analysis(self, df: pd.DataFrame) -> Optional[Dict]:
        """Комплексный технический анализ"""
        try:
            if len(df) < 50:
                logger.warning("Insufficient data for technical analysis")
                return None
            
            analysis = {}
            
            # Основные индикаторы
            analysis.update(self._calculate_trend_indicators(df))
            analysis.update(self._calculate_momentum_indicators(df))
            analysis.update(self._calculate_volatility_indicators(df))
            analysis.update(self._calculate_volume_indicators(df))
            
            # Текущая цена
            analysis['price'] = float(df['close'].iloc[-1])
            
            # Общая оценка
            analysis['overall_signal'] = self._get_overall_signal(analysis)
            
            return analysis
            
        except Exception as e:
            log_error("TechnicalAnalysis", e, "get_comprehensive_analysis")
            return None
    
    def _calculate_trend_indicators(self, df: pd.DataFrame) -> Dict:
        """Расчет трендовых индикаторов"""
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            
            indicators = {}
            
            # Moving Averages
            indicators['sma_20'] = float(talib.SMA(close, timeperiod=20)[-1])
            indicators['sma_50'] = float(talib.SMA(close, timeperiod=50)[-1])
            indicators['ema_12'] = float(talib.EMA(close, timeperiod=12)[-1])
            indicators['ema_26'] = float(talib.EMA(close, timeperiod=26)[-1])
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(close)
            indicators['macd'] = float(macd[-1])
            indicators['macd_signal'] = float(macd_signal[-1])
            indicators['macd_histogram'] = float(macd_hist[-1])
            
            # ADX (Average Directional Index)
            indicators['adx'] = float(talib.ADX(high, low, close, timeperiod=14)[-1])
            indicators['plus_di'] = float(talib.PLUS_DI(high, low, close, timeperiod=14)[-1])
            indicators['minus_di'] = float(talib.MINUS_DI(high, low, close, timeperiod=14)[-1])
            
            # Parabolic SAR
            indicators['sar'] = float(talib.SAR(high, low, acceleration=0.02, maximum=0.2)[-1])
            
            return indicators
            
        except Exception as e:
            log_error("TechnicalAnalysis", e, "_calculate_trend_indicators")
            return {}
    
    def _calculate_momentum_indicators(self, df: pd.DataFrame) -> Dict:
        """Расчет индикаторов импульса"""
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            
            indicators = {}
            
            # RSI
            indicators['rsi'] = float(talib.RSI(close, timeperiod=14)[-1])
            
            # Stochastic
            slowk, slowd = talib.STOCH(high, low, close)
            indicators['stoch_k'] = float(slowk[-1])
            indicators['stoch_d'] = float(slowd[-1])
            
            # Williams %R
            indicators['williams_r'] = float(talib.WILLR(high, low, close, timeperiod=14)[-1])
            
            # CCI (Commodity Channel Index)
            indicators['cci'] = float(talib.CCI(high, low, close, timeperiod=14)[-1])
            
            # ROC (Rate of Change)
            indicators['roc'] = float(talib.ROC(close, timeperiod=10)[-1])
            
            return indicators
            
        except Exception as e:
            log_error("TechnicalAnalysis", e, "_calculate_momentum_indicators")
            return {}
    
    def _calculate_volatility_indicators(self, df: pd.DataFrame) -> Dict:
        """Расчет индикаторов волатильности"""
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            
            indicators = {}
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
            indicators['bb_upper'] = float(bb_upper[-1])
            indicators['bb_middle'] = float(bb_middle[-1])
            indicators['bb_lower'] = float(bb_lower[-1])
            indicators['bb_width'] = float((bb_upper[-1] - bb_lower[-1]) / bb_middle[-1] * 100)
            
            # Average True Range
            indicators['atr'] = float(talib.ATR(high, low, close, timeperiod=14)[-1])
            
            # Keltner Channels
            ema = talib.EMA(close, timeperiod=20)
            atr = talib.ATR(high, low, close, timeperiod=10)
            indicators['keltner_upper'] = float(ema[-1] + (2 * atr[-1]))
            indicators['keltner_lower'] = float(ema[-1] - (2 * atr[-1]))
            
            return indicators
            
        except Exception as e:
            log_error("TechnicalAnalysis", e, "_calculate_volatility_indicators")
            return {}
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> Dict:
        """Расчет объемных индикаторов"""
        try:
            close = df['close'].values
            volume = df['volume'].values
            high = df['high'].values
            low = df['low'].values
            
            indicators = {}
            
            # Volume SMA
            indicators['volume_sma'] = float(talib.SMA(volume, timeperiod=20)[-1])
            
            # On Balance Volume
            indicators['obv'] = float(talib.OBV(close, volume)[-1])
            
            # Accumulation/Distribution Line
            indicators['ad'] = float(talib.AD(high, low, close, volume)[-1])
            
            # Chaikin Money Flow
            if len(df) >= 21:
                mfv = ((close - low) - (high - close)) / (high - low) * volume
                cmf = mfv.rolling(21).sum() / volume.rolling(21).sum()
                indicators['cmf'] = float(cmf.iloc[-1])
            
            return indicators
            
        except Exception as e:
            log_error("TechnicalAnalysis", e, "_calculate_volume_indicators")
            return {}
    
    def _get_overall_signal(self, analysis: Dict) -> str:
        """Определение общего сигнала на основе индикаторов"""
        try:
            signals = []
            
            # RSI сигналы
            rsi = analysis.get('rsi', 50)
            if rsi > 70:
                signals.append('SELL')
            elif rsi < 30:
                signals.append('BUY')
            else:
                signals.append('NEUTRAL')
            
            # MACD сигналы
            macd = analysis.get('macd', 0)
            macd_signal = analysis.get('macd_signal', 0)
            if macd > macd_signal:
                signals.append('BUY')
            else:
                signals.append('SELL')
            
            # Moving Average сигналы
            price = analysis.get('price', 0)
            sma_20 = analysis.get('sma_20', 0)
            if price > sma_20:
                signals.append('BUY')
            else:
                signals.append('SELL')
            
            # Bollinger Bands сигналы
            bb_upper = analysis.get('bb_upper', 0)
            bb_lower = analysis.get('bb_lower', 0)
            if price > bb_upper:
                signals.append('SELL')
            elif price < bb_lower:
                signals.append('BUY')
            else:
                signals.append('NEUTRAL')
            
            # Подсчет сигналов
            buy_signals = signals.count('BUY')
            sell_signals = signals.count('SELL')
            
            if buy_signals > sell_signals:
                return 'BUY'
            elif sell_signals > buy_signals:
                return 'SELL'
            else:
                return 'HOLD'
                
        except Exception as e:
            log_error("TechnicalAnalysis", e, "_get_overall_signal")
            return 'HOLD'
    
    def get_support_resistance_levels(self, df: pd.DataFrame) -> Dict:
        """Определение уровней поддержки и сопротивления"""
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            # Pivot Points
            pivot = (high[-1] + low[-1] + close[-1]) / 3
            
            # Support and Resistance levels
            r1 = 2 * pivot - low[-1]
            s1 = 2 * pivot - high[-1]
            r2 = pivot + (high[-1] - low[-1])
            s2 = pivot - (high[-1] - low[-1])
            
            # Find local highs and lows
            from scipy.signal import argrelextrema
            
            local_maxima = argrelextrema(high, np.greater, order=5)[0]
            local_minima = argrelextrema(low, np.less, order=5)[0]
            
            resistance_levels = [high[i] for i in local_maxima[-5:]]  # Last 5 resistance levels
            support_levels = [low[i] for i in local_minima[-5:]]     # Last 5 support levels
            
            return {
                'pivot': pivot,
                'resistance_1': r1,
                'resistance_2': r2,
                'support_1': s1,
                'support_2': s2,
                'resistance_levels': resistance_levels,
                'support_levels': support_levels
            }
            
        except Exception as e:
            log_error("TechnicalAnalysis", e, "get_support_resistance_levels")
            return {}
    
    def detect_patterns(self, df: pd.DataFrame) -> List[str]:
        """Обнаружение графических паттернов"""
        try:
            patterns = []
            
            open_prices = df['open'].values
            high_prices = df['high'].values
            low_prices = df['low'].values
            close_prices = df['close'].values
            
            # Candlestick patterns using TA-Lib
            
            # Doji
            if talib.CDLDOJI(open_prices, high_prices, low_prices, close_prices)[-1] != 0:
                patterns.append("Doji")
            
            # Hammer
            if talib.CDLHAMMER(open_prices, high_prices, low_prices, close_prices)[-1] != 0:
                patterns.append("Hammer")
            
            # Engulfing patterns
            if talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices)[-1] != 0:
                patterns.append("Engulfing")
            
            # Shooting Star
            if talib.CDLSHOOTINGSTAR(open_prices, high_prices, low_prices, close_prices)[-1] != 0:
                patterns.append("Shooting Star")
            
            # Morning Star
            if talib.CDLMORNINGSTAR(open_prices, high_prices, low_prices, close_prices)[-1] != 0:
                patterns.append("Morning Star")
            
            # Evening Star
            if talib.CDLEVENINGSTAR(open_prices, high_prices, low_prices, close_prices)[-1] != 0:
                patterns.append("Evening Star")
            
            return patterns
            
        except Exception as e:
            log_error("TechnicalAnalysis", e, "detect_patterns")
            return []
