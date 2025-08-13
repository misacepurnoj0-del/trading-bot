import hashlib
import hmac
import time
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime

from utils.logger import get_logger, log_error

logger = get_logger(__name__)

class MEXCClient:
    """Клиент для работы с MEXC API"""
    
    def __init__(self, api_key: str = "", secret_key: str = "", demo_mode: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.demo_mode = demo_mode
        
        self.base_url = "https://api.mexc.com"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-MEXC-APIKEY': self.api_key
        })
        
        logger.info(f"MEXC Client initialized - Demo: {demo_mode}")
    
    def _generate_signature(self, query_string: str) -> str:
        """Генерация подписи для запроса"""
        if not self.secret_key:
            return ""
        
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """Выполнение HTTP запроса"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if params is None:
                params = {}
            
            if signed and not self.demo_mode:
                params['timestamp'] = int(time.time() * 1000)
                query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                params['signature'] = self._generate_signature(query_string)
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=params)
            else:
                return {'error': f'Unsupported method: {method}'}
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'HTTP {response.status_code}: {response.text}'}
                
        except Exception as e:
            log_error("MEXCClient", e, f"Method: {method}, Endpoint: {endpoint}")
            return {'error': str(e)}
    
    def get_ticker_24hr(self, symbol: str = None) -> List[Dict]:
        """Получение 24-часовой статистики тикеров"""
        
        if self.demo_mode:
            # Возвращаем демо-данные
            return self._get_demo_tickers()
        
        endpoint = "/api/v3/ticker/24hr"
        params = {}
        
        if symbol:
            params['symbol'] = symbol
        
        result = self._make_request('GET', endpoint, params)
        
        if 'error' in result:
            logger.error(f"Error getting ticker data: {result['error']}")
            return []
        
        # Возвращаем список, даже если это один тикер
        return result if isinstance(result, list) else [result]
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List:
        """Получение данных свечей"""
        
        if self.demo_mode:
            return self._get_demo_klines(symbol, interval, limit)
        
        endpoint = "/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        result = self._make_request('GET', endpoint, params)
        
        if 'error' in result:
            logger.error(f"Error getting klines: {result['error']}")
            return []
        
        return result
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Получение стакана заявок"""
        
        if self.demo_mode:
            return self._get_demo_orderbook(symbol)
        
        endpoint = "/api/v3/depth"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return self._make_request('GET', endpoint, params)
    
    def get_account_info(self) -> Dict:
        """Получение информации об аккаунте"""
        
        if self.demo_mode:
            return self._get_demo_account()
        
        if not self.api_key or not self.secret_key:
            return {'error': 'API credentials not provided'}
        
        endpoint = "/api/v3/account"
        return self._make_request('GET', endpoint, signed=True)
    
    def place_order(self, symbol: str, side: str, order_type: str, 
                   quantity: float, price: float = None) -> Dict:
        """Размещение ордера"""
        
        if self.demo_mode:
            return self._place_demo_order(symbol, side, order_type, quantity, price)
        
        if not self.api_key or not self.secret_key:
            return {'error': 'API credentials not provided'}
        
        endpoint = "/api/v3/order"
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': quantity
        }
        
        if price and order_type.upper() == 'LIMIT':
            params['price'] = price
            params['timeInForce'] = 'GTC'
        
        return self._make_request('POST', endpoint, params, signed=True)
    
    def get_top_gainers_losers(self, limit: int = 20) -> List[Dict]:
        """Получение топ растущих/падающих активов"""
        
        tickers = self.get_ticker_24hr()
        
        if not tickers:
            return []
        
        # Фильтруем USDT пары и сортируем по изменению цены
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
        sorted_tickers = sorted(usdt_pairs, key=lambda x: float(x.get('priceChangePercent', 0)), reverse=True)
        
        return sorted_tickers[:limit]
    
    def get_volume_leaders(self, limit: int = 20) -> List[Dict]:
        """Получение лидеров по объему торгов"""
        
        tickers = self.get_ticker_24hr()
        
        if not tickers:
            return []
        
        # Фильтруем USDT пары и сортируем по объему
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
        sorted_tickers = sorted(usdt_pairs, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
        
        return sorted_tickers[:limit]
    
    def analyze_market_conditions(self) -> Dict:
        """Анализ общих рыночных условий"""
        
        try:
            tickers = self.get_ticker_24hr()
            
            if not tickers:
                return {'error': 'No ticker data available'}
            
            # Фильтруем USDT пары
            usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
            
            if not usdt_pairs:
                return {'error': 'No USDT pairs found'}
            
            # Анализ изменений цен
            price_changes = [float(t.get('priceChangePercent', 0)) for t in usdt_pairs]
            positive_changes = len([x for x in price_changes if x > 0])
            gainers_pct = (positive_changes / len(price_changes)) * 100
            
            # Средние значения
            avg_change_pct = sum(price_changes) / len(price_changes)
            total_volume_usdt = sum(float(t.get('quoteVolume', 0)) for t in usdt_pairs)
            
            # Определение настроения рынка
            if gainers_pct > 60 and avg_change_pct > 2:
                market_sentiment = 'Bullish'
            elif gainers_pct < 40 and avg_change_pct < -2:
                market_sentiment = 'Bearish'
            else:
                market_sentiment = 'Neutral'
            
            return {
                'market_sentiment': market_sentiment,
                'gainers_pct': gainers_pct,
                'avg_change_pct': avg_change_pct,
                'total_volume_usdt': total_volume_usdt,
                'total_pairs_analyzed': len(usdt_pairs),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error("MEXCClient", e, "analyze_market_conditions")
            return {'error': str(e)}
    
    def _get_demo_tickers(self) -> List[Dict]:
        """Демо-данные тикеров"""
        import random
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 
                  'SOLUSDT', 'DOTUSDT', 'LINKUSDT', 'LTCUSDT', 'BCHUSDT']
        
        demo_tickers = []
        for symbol in symbols:
            base_price = {'BTC': 45000, 'ETH': 3000, 'BNB': 300, 'ADA': 0.5, 'XRP': 0.6,
                         'SOL': 100, 'DOT': 7, 'LINK': 15, 'LTC': 70, 'BCH': 250}.get(
                         symbol.replace('USDT', ''), 100)
            
            change_pct = random.uniform(-10, 10)
            price = base_price * (1 + change_pct / 100)
            
            demo_tickers.append({
                'symbol': symbol,
                'lastPrice': str(price),
                'priceChangePercent': str(change_pct),
                'volume': str(random.uniform(1000, 100000)),
                'quoteVolume': str(random.uniform(1000000, 100000000)),
                'highPrice': str(price * 1.05),
                'lowPrice': str(price * 0.95),
                'openPrice': str(price / (1 + change_pct / 100))
            })
        
        return demo_tickers
    
    def _get_demo_klines(self, symbol: str, interval: str, limit: int) -> List:
        """Демо-данные свечей"""
        import random
        
        base_price = 45000 if 'BTC' in symbol else 3000
        klines = []
        
        current_time = int(time.time() * 1000)
        interval_ms = 3600000  # 1 hour
        
        for i in range(limit):
            timestamp = current_time - (limit - i) * interval_ms
            
            # Генерируем случайные данные свечи
            open_price = base_price * (1 + random.uniform(-0.02, 0.02))
            close_price = open_price * (1 + random.uniform(-0.01, 0.01))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.005))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.005))
            volume = random.uniform(100, 1000)
            
            klines.append([
                timestamp,          # Open time
                str(open_price),    # Open
                str(high_price),    # High
                str(low_price),     # Low
                str(close_price),   # Close
                str(volume),        # Volume
                timestamp + interval_ms - 1,  # Close time
                str(volume * close_price),     # Quote asset volume
                random.randint(50, 200),       # Number of trades
                str(volume * 0.6),            # Taker buy base asset volume
                str(volume * close_price * 0.6),  # Taker buy quote asset volume
                "0"                           # Ignore
            ])
        
        return klines
    
    def _get_demo_orderbook(self, symbol: str) -> Dict:
        """Демо-данные стакана"""
        import random
        
        base_price = 45000 if 'BTC' in symbol else 3000
        
        bids = []
        asks = []
        
        for i in range(10):
            bid_price = base_price * (1 - (i + 1) * 0.001)
            ask_price = base_price * (1 + (i + 1) * 0.001)
            quantity = random.uniform(0.1, 10)
            
            bids.append([str(bid_price), str(quantity)])
            asks.append([str(ask_price), str(quantity)])
        
        return {
            'bids': bids,
            'asks': asks,
            'lastUpdateId': int(time.time())
        }
    
    def _get_demo_account(self) -> Dict:
        """Демо-данные аккаунта"""
        return {
            'makerCommission': 10,
            'takerCommission': 10,
            'buyerCommission': 0,
            'sellerCommission': 0,
            'canTrade': True,
            'canWithdraw': True,
            'canDeposit': True,
            'balances': [
                {'asset': 'USDT', 'free': '10000.00000000', 'locked': '0.00000000'},
                {'asset': 'BTC', 'free': '0.50000000', 'locked': '0.00000000'},
                {'asset': 'ETH', 'free': '5.00000000', 'locked': '0.00000000'}
            ]
        }
    
    def _place_demo_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float, price: float = None) -> Dict:
        """Размещение демо-ордера"""
        import random
        
        return {
            'symbol': symbol,
            'orderId': random.randint(1000000, 9999999),
            'orderListId': -1,
            'clientOrderId': f'demo_{int(time.time())}',
            'transactTime': int(time.time() * 1000),
            'price': str(price) if price else '0.00000000',
            'origQty': str(quantity),
            'executedQty': str(quantity),
            'cummulativeQuoteQty': str(quantity * (price or 45000)),
            'status': 'FILLED',
            'timeInForce': 'GTC',
            'type': order_type.upper(),
            'side': side.upper()
        }
