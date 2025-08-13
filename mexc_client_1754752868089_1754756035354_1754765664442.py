import requests
import hmac
import hashlib
import time
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode
from utils.logger import get_logger

logger = get_logger(__name__)

class MEXCClient:
    """MEXC Exchange API Client"""
    
    def __init__(self, api_key: str = "", secret_key: str = "", demo_mode: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.demo_mode = demo_mode
        
        # MEXC API endpoints
        self.base_url = "https://api.mexc.com"
        self.spot_base_url = "https://api.mexc.com"
        
        # Demo mode simulation
        self.demo_balance = {
            'USDT': 10000.0,  # Starting demo balance
            'BTC': 0.0,
            'ETH': 0.0
        }
        
        logger.info(f"MEXC Client initialized - Demo mode: {demo_mode}")
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC signature for authenticated requests"""
        if not self.secret_key:
            return ""
        
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """Make HTTP request to MEXC API"""
        if self.demo_mode and signed:
            # Return demo data for authenticated endpoints
            return self._get_demo_response(endpoint, params)
        
        try:
            url = f"{self.base_url}{endpoint}"
            headers = {
                'X-MEXC-APIKEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            if params is None:
                params = {}
            
            if signed:
                timestamp = int(time.time() * 1000)
                params['timestamp'] = timestamp
                
                query_string = urlencode(params)
                signature = self._generate_signature(query_string)
                params['signature'] = signature
            
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"MEXC API request failed: {str(e)}")
            return {'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in MEXC request: {str(e)}")
            return {'error': str(e)}
    
    def _get_demo_response(self, endpoint: str, params: Dict = None) -> Dict:
        """Generate demo responses for testing"""
        if '/account' in endpoint:
            return {
                'balances': [
                    {'asset': asset, 'free': str(balance), 'locked': '0.0'}
                    for asset, balance in self.demo_balance.items()
                ]
            }
        elif '/order' in endpoint:
            return {
                'symbol': params.get('symbol', 'BTCUSDT'),
                'orderId': int(time.time()),
                'status': 'FILLED',
                'executedQty': params.get('quantity', '0'),
                'price': params.get('price', '0')
            }
        else:
            return {'demo': True, 'message': 'Demo mode response'}
    
    def get_server_time(self) -> Dict:
        """Get MEXC server time"""
        return self._make_request('GET', '/api/v3/time')
    
    def get_exchange_info(self) -> Dict:
        """Get exchange information"""
        return self._make_request('GET', '/api/v3/exchangeInfo')
    
    def get_ticker_24hr(self, symbol: str = "") -> Dict:
        """Get 24hr ticker price change statistics"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return self._make_request('GET', '/api/v3/ticker/24hr', params)
    
    def get_ticker_price(self, symbol: str = "") -> Dict:
        """Get symbol price ticker"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return self._make_request('GET', '/api/v3/ticker/price', params)
    
    def get_orderbook(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book depth"""
        params = {'symbol': symbol, 'limit': limit}
        return self._make_request('GET', '/api/v3/depth', params)
    
    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 500) -> Dict:
        """Get kline/candlestick data"""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        return self._make_request('GET', '/api/v3/klines', params)
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        return self._make_request('GET', '/api/v3/account', signed=True)
    
    def get_open_orders(self, symbol: str = "") -> Dict:
        """Get all open orders"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return self._make_request('GET', '/api/v3/openOrders', params, signed=True)
    
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, 
                   price: float = None, time_in_force: str = 'GTC') -> Dict:
        """Place a new order"""
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': str(quantity),
            'timeInForce': time_in_force
        }
        
        if price and order_type.upper() in ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT']:
            params['price'] = str(price)
        
        logger.info(f"Placing order: {side} {quantity} {symbol} at {price}")
        return self._make_request('POST', '/api/v3/order', params, signed=True)
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel an active order"""
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        
        return self._make_request('DELETE', '/api/v3/order', params, signed=True)
    
    def get_order_status(self, symbol: str, order_id: int) -> Dict:
        """Get order status"""
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        
        return self._make_request('GET', '/api/v3/order', params, signed=True)
    
    def get_trade_history(self, symbol: str, limit: int = 500) -> Dict:
        """Get trade history"""
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return self._make_request('GET', '/api/v3/myTrades', params, signed=True)
    
    def get_top_gainers_losers(self, limit: int = 50) -> List[Dict]:
        """Get top gaining and losing symbols"""
        try:
            tickers = self.get_ticker_24hr()
            
            if isinstance(tickers, list):
                # Sort by price change percentage
                sorted_tickers = sorted(
                    tickers, 
                    key=lambda x: float(x.get('priceChangePercent', 0)), 
                    reverse=True
                )
                
                # Filter USDT pairs and return top performers
                usdt_pairs = [t for t in sorted_tickers if t['symbol'].endswith('USDT')]
                return usdt_pairs[:limit]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting top gainers/losers: {str(e)}")
            return []
    
    def get_volume_leaders(self, limit: int = 50) -> List[Dict]:
        """Get symbols with highest 24hr volume"""
        try:
            tickers = self.get_ticker_24hr()
            
            if isinstance(tickers, list):
                # Sort by volume
                sorted_tickers = sorted(
                    tickers,
                    key=lambda x: float(x.get('volume', 0)),
                    reverse=True
                )
                
                # Filter USDT pairs
                usdt_pairs = [t for t in sorted_tickers if t['symbol'].endswith('USDT')]
                return usdt_pairs[:limit]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting volume leaders: {str(e)}")
            return []
    
    def analyze_market_conditions(self) -> Dict:
        """Analyze overall market conditions"""
        try:
            tickers = self.get_ticker_24hr()
            
            if not isinstance(tickers, list):
                return {'error': 'Unable to fetch market data'}
            
            # Filter USDT pairs for analysis
            usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
            
            if not usdt_pairs:
                return {'error': 'No USDT pairs found'}
            
            # Calculate market statistics
            total_symbols = len(usdt_pairs)
            gainers = len([t for t in usdt_pairs if float(t.get('priceChangePercent', 0)) > 0])
            losers = len([t for t in usdt_pairs if float(t.get('priceChangePercent', 0)) < 0])
            
            avg_change = sum(float(t.get('priceChangePercent', 0)) for t in usdt_pairs) / total_symbols
            total_volume = sum(float(t.get('quoteVolume', 0)) for t in usdt_pairs)
            
            # Determine market sentiment
            if gainers > losers * 1.5:
                sentiment = "Bullish"
            elif losers > gainers * 1.5:
                sentiment = "Bearish"
            else:
                sentiment = "Neutral"
            
            return {
                'total_symbols': total_symbols,
                'gainers': gainers,
                'losers': losers,
                'gainers_pct': (gainers / total_symbols) * 100,
                'avg_change_pct': avg_change,
                'total_volume_usdt': total_volume,
                'market_sentiment': sentiment
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {str(e)}")
            return {'error': str(e)}
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get detailed information about a specific symbol"""
        try:
            # Get basic ticker info
            ticker = self.get_ticker_24hr(symbol)
            
            if 'error' in ticker:
                return ticker
            
            # Get order book for spread analysis
            orderbook = self.get_orderbook(symbol, 10)
            
            spread = 0.0
            if 'bids' in orderbook and 'asks' in orderbook and orderbook['bids'] and orderbook['asks']:
                best_bid = float(orderbook['bids'][0][0])
                best_ask = float(orderbook['asks'][0][0])
                spread = ((best_ask - best_bid) / best_bid) * 100
            
            return {
                'symbol': symbol,
                'price': float(ticker.get('lastPrice', 0)),
                'change_24h': float(ticker.get('priceChangePercent', 0)),
                'volume_24h': float(ticker.get('volume', 0)),
                'quote_volume_24h': float(ticker.get('quoteVolume', 0)),
                'high_24h': float(ticker.get('highPrice', 0)),
                'low_24h': float(ticker.get('lowPrice', 0)),
                'spread_pct': spread,
                'trade_count': int(ticker.get('count', 0))
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {str(e)}")
            return {'error': str(e)}
