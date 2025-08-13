import requests
import hmac
import hashlib
import time
import json
import asyncio
import websockets
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode
from decimal import Decimal
import os
from utils.logger import get_logger, log_api_call, log_trading_action

logger = get_logger(__name__)

class MEXCClient:
    """Advanced MEXC Exchange API Client with Spot and Futures support"""
    
    def __init__(self, api_key: str = "", secret_key: str = "", demo_mode: bool = True):
        self.api_key = api_key or os.getenv("MEXC_API_KEY", "")
        self.secret_key = secret_key or os.getenv("MEXC_SECRET_KEY", "")
        self.demo_mode = demo_mode
        
        # MEXC API endpoints
        self.spot_base_url = "https://api.mexc.com"
        self.futures_base_url = "https://contract.mexc.com"
        self.ws_spot_url = "wss://wbs.mexc.com/ws"
        self.ws_futures_url = "wss://contract.mexc.com/ws"
        
        # Rate limiting
        self.request_weights = {}
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Demo mode simulation
        self.demo_balance = {
            'USDT': 10000.0,
            'BTC': 0.0,
            'ETH': 0.0,
            'BNB': 0.0
        }
        
        # Futures demo positions
        self.demo_futures_positions = {}
        self.demo_futures_balance = {'USDT': 5000.0}
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'X-MEXC-APIKEY': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'MEXC-AI-Trader/1.0'
        })
        
        logger.info(f"MEXC Advanced Client initialized - Demo mode: {demo_mode}")
    
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC signature for authenticated requests"""
        if not self.secret_key:
            return ""
        
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     signed: bool = False, futures: bool = False) -> Dict:
        """Make HTTP request to MEXC API with comprehensive error handling"""
        
        if self.demo_mode and signed:
            return self._get_demo_response(endpoint, params, futures)
        
        self._rate_limit()
        
        try:
            base_url = self.futures_base_url if futures else self.spot_base_url
            url = f"{base_url}{endpoint}"
            
            if params is None:
                params = {}
            
            if signed:
                timestamp = int(time.time() * 1000)
                params['timestamp'] = timestamp
                params['recvWindow'] = 5000
                
                query_string = urlencode(sorted(params.items()))
                signature = self._generate_signature(query_string)
                params['signature'] = signature
            
            start_time = time.time()
            
            if method == 'GET':
                response = self.session.get(url, params=params, timeout=30)
            elif method == 'POST':
                response = self.session.post(url, json=params, timeout=30)
            elif method == 'PUT':
                response = self.session.put(url, json=params, timeout=30)
            elif method == 'DELETE':
                response = self.session.delete(url, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response_time = time.time() - start_time
            
            # Log API call
            log_api_call("MEXC", endpoint, response.status_code == 200, response_time)
            
            response.raise_for_status()
            result = response.json()
            
            # Handle MEXC specific error responses
            if isinstance(result, dict):
                if 'code' in result and result['code'] != 200:
                    error_msg = result.get('msg', f"API Error {result['code']}")
                    logger.error(f"MEXC API error: {error_msg}")
                    return {'error': error_msg}
            
            return result
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"MEXC API HTTP error: {error_msg}")
            log_api_call("MEXC", endpoint, False, 0, error_msg)
            return {'error': error_msg}
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"MEXC API request error: {error_msg}")
            log_api_call("MEXC", endpoint, False, 0, error_msg)
            return {'error': error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"MEXC API unexpected error: {error_msg}")
            log_api_call("MEXC", endpoint, False, 0, error_msg)
            return {'error': error_msg}
    
    def _get_demo_response(self, endpoint: str, params: Dict = None, futures: bool = False) -> Dict:
        """Generate realistic demo responses for testing"""
        
        if params is None:
            params = {}
            
        # Account endpoints
        if '/account' in endpoint:
            if futures:
                return {
                    'totalWalletBalance': str(self.demo_futures_balance.get('USDT', 0)),
                    'totalUnrealizedProfit': '0.0',
                    'totalMarginBalance': str(self.demo_futures_balance.get('USDT', 0)),
                    'totalPositionInitialMargin': '0.0',
                    'assets': [
                        {
                            'asset': 'USDT',
                            'walletBalance': str(self.demo_futures_balance.get('USDT', 0)),
                            'unrealizedProfit': '0.0',
                            'marginBalance': str(self.demo_futures_balance.get('USDT', 0))
                        }
                    ]
                }
            else:
                return {
                    'balances': [
                        {'asset': asset, 'free': str(balance), 'locked': '0.0'}
                        for asset, balance in self.demo_balance.items()
                        if balance > 0
                    ]
                }
        
        # Order endpoints
        elif '/order' in endpoint:
            order_id = int(time.time() * 1000)
            return {
                'symbol': params.get('symbol', 'BTCUSDT'),
                'orderId': order_id,
                'clientOrderId': f"demo_{order_id}",
                'status': 'FILLED',
                'executedQty': params.get('quantity', '0'),
                'price': params.get('price', '0'),
                'side': params.get('side', 'BUY'),
                'type': params.get('type', 'MARKET'),
                'timeInForce': 'GTC',
                'transactTime': int(time.time() * 1000)
            }
        
        # Position endpoints (futures)
        elif '/positionRisk' in endpoint:
            return list(self.demo_futures_positions.values())
        
        # Default response
        else:
            return {'demo': True, 'message': 'Demo mode response'}
    
    # SPOT TRADING METHODS
    
    def get_server_time(self) -> Dict:
        """Get MEXC server time"""
        return self._make_request('GET', '/api/v3/time')
    
    def get_exchange_info(self) -> Dict:
        """Get spot exchange information"""
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
        params = {'symbol': symbol, 'limit': min(limit, 5000)}
        return self._make_request('GET', '/api/v3/depth', params)
    
    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 500, 
                   start_time: int = None, end_time: int = None) -> List:
        """Get kline/candlestick data with extended parameters"""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, 1000)
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        result = self._make_request('GET', '/api/v3/klines', params)
        
        # Return the data directly if it's a list, otherwise handle error
        if isinstance(result, list):
            return result
        elif 'error' in result:
            logger.error(f"Error fetching klines: {result['error']}")
            return []
        else:
            return result.get('data', [])
    
    def get_account_info(self) -> Dict:
        """Get spot account information"""
        return self._make_request('GET', '/api/v3/account', signed=True)
    
    def get_open_orders(self, symbol: str = "") -> Dict:
        """Get all open spot orders"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._make_request('GET', '/api/v3/openOrders', params, signed=True)
    
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, 
                   price: float = None, time_in_force: str = 'GTC', 
                   stop_price: float = None, iceberg_qty: float = None,
                   new_order_resp_type: str = 'RESULT') -> Dict:
        """Place a new spot order with advanced parameters"""
        
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': str(quantity),
            'newOrderRespType': new_order_resp_type
        }
        
        if order_type.upper() in ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT']:
            if not price:
                return {'error': 'Price required for limit orders'}
            params['price'] = str(price)
            params['timeInForce'] = time_in_force
        
        if order_type.upper() in ['STOP_LOSS', 'STOP_LOSS_LIMIT']:
            if not stop_price:
                return {'error': 'Stop price required for stop orders'}
            params['stopPrice'] = str(stop_price)
        
        if order_type.upper() in ['TAKE_PROFIT', 'TAKE_PROFIT_LIMIT']:
            if not stop_price:
                return {'error': 'Stop price required for take profit orders'}
            params['stopPrice'] = str(stop_price)
        
        if iceberg_qty:
            params['icebergQty'] = str(iceberg_qty)
        
        log_trading_action("PLACE_SPOT_ORDER", symbol, params)
        return self._make_request('POST', '/api/v3/order', params, signed=True)
    
    def cancel_order(self, symbol: str, order_id: int = None, 
                    orig_client_order_id: str = None) -> Dict:
        """Cancel an active spot order"""
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        else:
            return {'error': 'Either orderId or origClientOrderId required'}
        
        log_trading_action("CANCEL_SPOT_ORDER", symbol, params)
        return self._make_request('DELETE', '/api/v3/order', params, signed=True)
    
    def get_order_status(self, symbol: str, order_id: int = None, 
                        orig_client_order_id: str = None) -> Dict:
        """Get spot order status"""
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        else:
            return {'error': 'Either orderId or origClientOrderId required'}
        
        return self._make_request('GET', '/api/v3/order', params, signed=True)
    
    def get_trade_history(self, symbol: str, limit: int = 500, from_id: int = None) -> Dict:
        """Get spot trade history"""
        params = {'symbol': symbol, 'limit': min(limit, 1000)}
        if from_id:
            params['fromId'] = from_id
        
        return self._make_request('GET', '/api/v3/myTrades', params, signed=True)
    
    # FUTURES TRADING METHODS
    
    def get_futures_exchange_info(self) -> Dict:
        """Get futures exchange information"""
        return self._make_request('GET', '/api/v1/exchangeInfo', futures=True)
    
    def get_futures_ticker(self, symbol: str = "") -> Dict:
        """Get futures ticker information"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._make_request('GET', '/api/v1/ticker/24hr', params, futures=True)
    
    def get_futures_orderbook(self, symbol: str, limit: int = 100) -> Dict:
        """Get futures order book depth"""
        params = {'symbol': symbol, 'limit': min(limit, 1000)}
        return self._make_request('GET', '/api/v1/depth', params, futures=True)
    
    def get_futures_klines(self, symbol: str, interval: str = '1h', limit: int = 500) -> List:
        """Get futures kline/candlestick data"""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, 1500)
        }
        
        result = self._make_request('GET', '/api/v1/klines', params, futures=True)
        
        if isinstance(result, list):
            return result
        elif 'error' in result:
            logger.error(f"Error fetching futures klines: {result['error']}")
            return []
        else:
            return result.get('data', [])
    
    def get_futures_account(self) -> Dict:
        """Get futures account information"""
        return self._make_request('GET', '/api/v2/account', signed=True, futures=True)
    
    def get_futures_positions(self) -> Dict:
        """Get futures position information"""
        return self._make_request('GET', '/api/v2/positionRisk', signed=True, futures=True)
    
    def place_futures_order(self, symbol: str, side: str, order_type: str, quantity: float,
                           price: float = None, reduce_only: bool = False,
                           time_in_force: str = 'GTC', stop_price: float = None) -> Dict:
        """Place a new futures order"""
        
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': str(quantity),
        }
        
        if order_type.upper() in ['LIMIT', 'STOP', 'TAKE_PROFIT']:
            if not price:
                return {'error': 'Price required for limit orders'}
            params['price'] = str(price)
            params['timeInForce'] = time_in_force
        
        if order_type.upper() in ['STOP', 'STOP_MARKET']:
            if not stop_price:
                return {'error': 'Stop price required for stop orders'}
            params['stopPrice'] = str(stop_price)
        
        if order_type.upper() in ['TAKE_PROFIT', 'TAKE_PROFIT_MARKET']:
            if not stop_price:
                return {'error': 'Stop price required for take profit orders'}
            params['stopPrice'] = str(stop_price)
        
        if reduce_only:
            params['reduceOnly'] = 'true'
        
        log_trading_action("PLACE_FUTURES_ORDER", symbol, params)
        return self._make_request('POST', '/api/v1/order', params, signed=True, futures=True)
    
    def cancel_futures_order(self, symbol: str, order_id: int = None,
                            orig_client_order_id: str = None) -> Dict:
        """Cancel a futures order"""
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        else:
            return {'error': 'Either orderId or origClientOrderId required'}
        
        log_trading_action("CANCEL_FUTURES_ORDER", symbol, params)
        return self._make_request('DELETE', '/api/v1/order', params, signed=True, futures=True)
    
    def get_futures_open_orders(self, symbol: str = "") -> Dict:
        """Get open futures orders"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._make_request('GET', '/api/v1/openOrders', params, signed=True, futures=True)
    
    def change_futures_leverage(self, symbol: str, leverage: int) -> Dict:
        """Change futures leverage"""
        params = {
            'symbol': symbol,
            'leverage': leverage
        }
        
        log_trading_action("CHANGE_LEVERAGE", symbol, {'leverage': leverage})
        return self._make_request('POST', '/api/v1/leverage', params, signed=True, futures=True)
    
    def change_margin_type(self, symbol: str, margin_type: str) -> Dict:
        """Change margin type (ISOLATED/CROSSED)"""
        params = {
            'symbol': symbol,
            'marginType': margin_type.upper()
        }
        
        return self._make_request('POST', '/api/v1/marginType', params, signed=True, futures=True)
    
    # ADVANCED MARKET ANALYSIS METHODS
    
    def get_top_gainers_losers(self, limit: int = 50) -> List[Dict]:
        """Get top gaining and losing symbols with enhanced filtering"""
        try:
            tickers = self.get_ticker_24hr()
            
            if isinstance(tickers, list):
                # Filter and sort
                usdt_pairs = [
                    t for t in tickers 
                    if t['symbol'].endswith('USDT') and 
                    float(t.get('volume', 0)) > 10000 and  # Minimum volume filter
                    float(t.get('quoteVolume', 0)) > 100000  # Minimum quote volume
                ]
                
                # Sort by price change percentage
                sorted_tickers = sorted(
                    usdt_pairs, 
                    key=lambda x: float(x.get('priceChangePercent', 0)), 
                    reverse=True
                )
                
                return sorted_tickers[:limit]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting top gainers/losers: {str(e)}")
            return []
    
    def get_volume_leaders(self, limit: int = 50) -> List[Dict]:
        """Get symbols with highest 24hr volume"""
        try:
            tickers = self.get_ticker_24hr()
            
            if isinstance(tickers, list):
                # Filter USDT pairs with minimum criteria
                usdt_pairs = [
                    t for t in tickers 
                    if t['symbol'].endswith('USDT') and 
                    float(t.get('quoteVolume', 0)) > 50000  # Minimum quote volume
                ]
                
                # Sort by quote volume (USDT volume)
                sorted_tickers = sorted(
                    usdt_pairs,
                    key=lambda x: float(x.get('quoteVolume', 0)),
                    reverse=True
                )
                
                return sorted_tickers[:limit]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting volume leaders: {str(e)}")
            return []
    
    def analyze_market_conditions(self) -> Dict:
        """Comprehensive market condition analysis"""
        try:
            tickers = self.get_ticker_24hr()
            
            if not isinstance(tickers, list):
                return {'error': 'Unable to fetch market data'}
            
            # Filter USDT pairs for analysis
            usdt_pairs = [
                t for t in tickers 
                if t['symbol'].endswith('USDT') and 
                float(t.get('volume', 0)) > 1000  # Basic volume filter
            ]
            
            if not usdt_pairs:
                return {'error': 'No USDT pairs found'}
            
            # Calculate comprehensive market statistics
            total_symbols = len(usdt_pairs)
            price_changes = [float(t.get('priceChangePercent', 0)) for t in usdt_pairs]
            
            gainers = len([p for p in price_changes if p > 0])
            losers = len([p for p in price_changes if p < 0])
            strong_gainers = len([p for p in price_changes if p > 5])
            strong_losers = len([p for p in price_changes if p < -5])
            
            avg_change = sum(price_changes) / total_symbols
            total_volume = sum(float(t.get('quoteVolume', 0)) for t in usdt_pairs)
            
            # Advanced market sentiment calculation
            if strong_gainers > strong_losers * 2:
                sentiment = "Very Bullish"
            elif gainers > losers * 1.5:
                sentiment = "Bullish"
            elif strong_losers > strong_gainers * 2:
                sentiment = "Very Bearish"
            elif losers > gainers * 1.5:
                sentiment = "Bearish"
            else:
                sentiment = "Neutral"
            
            # Market volatility assessment
            volatility_scores = [abs(p) for p in price_changes]
            avg_volatility = sum(volatility_scores) / len(volatility_scores)
            
            if avg_volatility > 8:
                volatility_level = "Very High"
            elif avg_volatility > 5:
                volatility_level = "High"
            elif avg_volatility > 3:
                volatility_level = "Moderate"
            else:
                volatility_level = "Low"
            
            return {
                'total_symbols': total_symbols,
                'gainers': gainers,
                'losers': losers,
                'strong_gainers': strong_gainers,
                'strong_losers': strong_losers,
                'gainers_pct': (gainers / total_symbols) * 100,
                'losers_pct': (losers / total_symbols) * 100,
                'avg_change_pct': avg_change,
                'total_volume_usdt': total_volume,
                'market_sentiment': sentiment,
                'volatility_level': volatility_level,
                'avg_volatility': avg_volatility,
                'analysis_timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {str(e)}")
            return {'error': str(e)}
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get comprehensive information about a specific symbol"""
        try:
            # Get basic ticker info
            ticker = self.get_ticker_24hr(symbol)
            
            if 'error' in ticker:
                return ticker
            
            # Get order book for spread analysis
            orderbook = self.get_orderbook(symbol, 10)
            
            spread = 0.0
            bid_ask_ratio = 0.0
            
            if 'bids' in orderbook and 'asks' in orderbook:
                bids = orderbook.get('bids', [])
                asks = orderbook.get('asks', [])
                
                if bids and asks:
                    best_bid = float(bids[0][0])
                    best_ask = float(asks[0][0])
                    
                    if best_bid > 0:
                        spread = ((best_ask - best_bid) / best_bid) * 100
                        
                    # Calculate bid/ask volume ratio
                    total_bid_volume = sum(float(bid[1]) for bid in bids[:5])
                    total_ask_volume = sum(float(ask[1]) for ask in asks[:5])
                    
                    if total_ask_volume > 0:
                        bid_ask_ratio = total_bid_volume / total_ask_volume
            
            # Technical indicators
            current_price = float(ticker.get('lastPrice', 0))
            high_24h = float(ticker.get('highPrice', 0))
            low_24h = float(ticker.get('lowPrice', 0))
            
            # Price position within 24h range
            if high_24h > low_24h:
                price_position = ((current_price - low_24h) / (high_24h - low_24h)) * 100
            else:
                price_position = 50.0
            
            return {
                'symbol': symbol,
                'price': current_price,
                'change_24h': float(ticker.get('priceChangePercent', 0)),
                'volume_24h': float(ticker.get('volume', 0)),
                'quote_volume_24h': float(ticker.get('quoteVolume', 0)),
                'high_24h': high_24h,
                'low_24h': low_24h,
                'open_price': float(ticker.get('openPrice', 0)),
                'prev_close': float(ticker.get('prevClosePrice', 0)),
                'spread_pct': spread,
                'bid_ask_ratio': bid_ask_ratio,
                'price_position_pct': price_position,
                'trade_count': int(ticker.get('count', 0)),
                'weighted_avg_price': float(ticker.get('weightedAvgPrice', 0)),
                'analysis_timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {str(e)}")
            return {'error': str(e)}
    
    def get_market_depth_analysis(self, symbol: str, limit: int = 100) -> Dict:
        """Analyze market depth and liquidity"""
        try:
            orderbook = self.get_orderbook(symbol, limit)
            
            if 'error' in orderbook:
                return orderbook
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return {'error': 'Insufficient orderbook data'}
            
            # Calculate depth metrics
            bid_prices = [float(bid[0]) for bid in bids]
            bid_volumes = [float(bid[1]) for bid in bids]
            ask_prices = [float(ask[0]) for ask in asks]
            ask_volumes = [float(ask[1]) for ask in asks]
            
            # Liquidity analysis
            total_bid_volume = sum(bid_volumes)
            total_ask_volume = sum(ask_volumes)
            
            # Support and resistance levels
            significant_bid_levels = []
            significant_ask_levels = []
            
            # Find significant bid levels (volume > 2x average)
            avg_bid_volume = total_bid_volume / len(bid_volumes)
            for i, (price, volume) in enumerate(zip(bid_prices, bid_volumes)):
                if volume > avg_bid_volume * 2:
                    significant_bid_levels.append({'price': price, 'volume': volume})
            
            # Find significant ask levels
            avg_ask_volume = total_ask_volume / len(ask_volumes)
            for i, (price, volume) in enumerate(zip(ask_prices, ask_volumes)):
                if volume > avg_ask_volume * 2:
                    significant_ask_levels.append({'price': price, 'volume': volume})
            
            # Market pressure analysis
            if total_bid_volume > total_ask_volume * 1.2:
                market_pressure = "Bullish"
            elif total_ask_volume > total_bid_volume * 1.2:
                market_pressure = "Bearish"
            else:
                market_pressure = "Neutral"
            
            return {
                'symbol': symbol,
                'total_bid_volume': total_bid_volume,
                'total_ask_volume': total_ask_volume,
                'bid_ask_volume_ratio': total_bid_volume / total_ask_volume if total_ask_volume > 0 else 0,
                'market_pressure': market_pressure,
                'significant_bid_levels': significant_bid_levels[:5],
                'significant_ask_levels': significant_ask_levels[:5],
                'depth_imbalance': abs(total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume),
                'liquidity_score': min((total_bid_volume + total_ask_volume) / 1000000, 1.0),  # Normalized to 1.0
                'analysis_timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market depth for {symbol}: {str(e)}")
            return {'error': str(e)}
    
    async def get_real_time_data(self, symbol: str, callback) -> None:
        """Get real-time data via WebSocket"""
        try:
            uri = f"{self.ws_spot_url}"
            
            async with websockets.connect(uri) as websocket:
                # Subscribe to ticker stream
                subscribe_msg = {
                    "method": "SUBSCRIPTION",
                    "params": [f"{symbol.lower()}@ticker"]
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                
                async for message in websocket:
                    data = json.loads(message)
                    await callback(data)
                    
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
    
    def close_session(self):
        """Close the requests session"""
        try:
            self.session.close()
            logger.info("MEXC client session closed")
        except Exception as e:
            logger.warning(f"Error closing session: {str(e)}")
