import requests
import feedparser
import trafilatura
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
import time

from utils.logger import get_logger, log_error

logger = get_logger(__name__)

class NewsParser:
    """Парсер новостей и анализ настроений"""
    
    def __init__(self):
        self.news_sources = {
            'cointelegraph': 'https://cointelegraph.com/rss',
            'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
            'decrypt': 'https://decrypt.co/feed',
            'cryptonews': 'https://cryptonews.com/news/feed',
            'bitcoinist': 'https://bitcoinist.com/feed/',
            'ccn': 'https://www.ccn.com/feed/',
            'cryptopotato': 'https://cryptopotato.com/feed/',
            'newsbtc': 'https://www.newsbtc.com/feed/',
            'coinspeaker': 'https://www.coinspeaker.com/feed/',
            'cryptoslate': 'https://cryptoslate.com/feed/'
        }
        
        self.sentiment_keywords = {
            'bullish': [
                'bullish', 'rally', 'surge', 'pump', 'moon', 'breakout', 'gains',
                'bull market', 'positive', 'optimistic', 'growth', 'rise', 'upward',
                'breakthrough', 'adoption', 'partnership', 'investment', 'buying'
            ],
            'bearish': [
                'bearish', 'crash', 'dump', 'fall', 'decline', 'drop', 'bear market',
                'negative', 'pessimistic', 'sell-off', 'correction', 'fear', 'panic',
                'regulation', 'ban', 'crackdown', 'hack', 'scam', 'loss'
            ],
            'neutral': [
                'stable', 'sideways', 'consolidation', 'neutral', 'analysis',
                'review', 'update', 'announcement', 'discussion', 'interview'
            ]
        }
        
        # Кэш для новостей
        self.news_cache = {}
        self.last_update = None
        
    def get_market_sentiment(self, hours_back: int = 24) -> Dict:
        """Получение общего настроения рынка на основе новостей"""
        try:
            # Проверяем кэш
            if self._is_cache_valid():
                return self.news_cache.get('market_sentiment', {})
            
            all_news = []
            
            # Собираем новости из всех источников
            for source_name, rss_url in self.news_sources.items():
                try:
                    news_items = self._parse_rss_feed(rss_url, hours_back)
                    all_news.extend(news_items)
                    time.sleep(1)  # Пауза между запросами
                except Exception as e:
                    logger.warning(f"Failed to parse {source_name}: {str(e)}")
                    continue
            
            if not all_news:
                return self._get_neutral_sentiment()
            
            # Анализируем настроения
            sentiment_analysis = self._analyze_news_sentiment(all_news)
            
            # Кэшируем результат
            self.news_cache['market_sentiment'] = sentiment_analysis
            self.last_update = datetime.now()
            
            return sentiment_analysis
            
        except Exception as e:
            log_error("NewsParser", e, "get_market_sentiment")
            return self._get_neutral_sentiment()
    
    def get_symbol_news(self, symbol: str, hours_back: int = 24) -> List[Dict]:
        """Получение новостей по конкретному символу"""
        try:
            # Извлекаем базовый актив (например, BTC из BTCUSDT)
            base_asset = symbol.replace('USDT', '').replace('BUSD', '').replace('USD', '')
            
            # Поисковые термины для актива
            search_terms = [base_asset.lower()]
            
            # Добавляем полные названия для популярных криптовалют
            crypto_names = {
                'BTC': ['bitcoin', 'btc'],
                'ETH': ['ethereum', 'eth', 'ether'],
                'BNB': ['binance', 'bnb', 'binance coin'],
                'ADA': ['cardano', 'ada'],
                'XRP': ['ripple', 'xrp'],
                'SOL': ['solana', 'sol'],
                'DOT': ['polkadot', 'dot'],
                'LINK': ['chainlink', 'link'],
                'LTC': ['litecoin', 'ltc'],
                'BCH': ['bitcoin cash', 'bch']
            }
            
            if base_asset in crypto_names:
                search_terms.extend(crypto_names[base_asset])
            
            symbol_news = []
            
            # Получаем все новости
            market_sentiment = self.get_market_sentiment(hours_back)
            all_news = market_sentiment.get('news_items', [])
            
            # Фильтруем новости по символу
            for news_item in all_news:
                title = news_item.get('title', '').lower()
                description = news_item.get('description', '').lower()
                
                # Проверяем наличие поисковых терминов
                if any(term in title or term in description for term in search_terms):
                    symbol_news.append(news_item)
            
            return symbol_news[:10]  # Возвращаем топ-10 новостей
            
        except Exception as e:
            log_error("NewsParser", e, f"get_symbol_news for {symbol}")
            return []
    
    def _parse_rss_feed(self, rss_url: str, hours_back: int) -> List[Dict]:
        """Парсинг RSS фида"""
        try:
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                return []
            
            news_items = []
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for entry in feed.entries[:20]:  # Ограничиваем количество
                try:
                    # Парсим дату публикации
                    pub_date = datetime(*entry.published_parsed[:6])
                    
                    if pub_date < cutoff_time:
                        continue
                    
                    # Извлекаем полный текст статьи
                    full_text = ""
                    if hasattr(entry, 'link'):
                        try:
                            downloaded = trafilatura.fetch_url(entry.link)
                            if downloaded:
                                full_text = trafilatura.extract(downloaded) or ""
                        except:
                            pass
                    
                    news_item = {
                        'title': entry.title,
                        'description': getattr(entry, 'description', ''),
                        'link': getattr(entry, 'link', ''),
                        'published': pub_date.isoformat(),
                        'source': rss_url,
                        'full_text': full_text[:1000]  # Ограничиваем размер
                    }
                    
                    news_items.append(news_item)
                    
                except Exception as e:
                    logger.warning(f"Error parsing entry: {str(e)}")
                    continue
            
            return news_items
            
        except Exception as e:
            log_error("NewsParser", e, f"_parse_rss_feed: {rss_url}")
            return []
    
    def _analyze_news_sentiment(self, news_items: List[Dict]) -> Dict:
        """Анализ настроений новостей"""
        try:
            if not news_items:
                return self._get_neutral_sentiment()
            
            sentiment_scores = []
            
            for news_item in news_items:
                # Объединяем заголовок, описание и текст для анализа
                text = f"{news_item.get('title', '')} {news_item.get('description', '')} {news_item.get('full_text', '')}"
                text = text.lower()
                
                # Подсчитываем ключевые слова
                bullish_count = sum(1 for keyword in self.sentiment_keywords['bullish'] if keyword in text)
                bearish_count = sum(1 for keyword in self.sentiment_keywords['bearish'] if keyword in text)
                neutral_count = sum(1 for keyword in self.sentiment_keywords['neutral'] if keyword in text)
                
                # Вычисляем оценку настроения (-1 до 1)
                total_keywords = bullish_count + bearish_count + neutral_count
                
                if total_keywords == 0:
                    sentiment_score = 0  # Нейтральный
                else:
                    sentiment_score = (bullish_count - bearish_count) / max(total_keywords, 1)
                
                sentiment_scores.append(sentiment_score)
            
            # Общая оценка настроения
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            # Определяем общее настроение
            if avg_sentiment > 0.2:
                overall_sentiment = 'Bullish'
            elif avg_sentiment < -0.2:
                overall_sentiment = 'Bearish'
            else:
                overall_sentiment = 'Neutral'
            
            # Подсчитываем статистику
            bullish_news = len([s for s in sentiment_scores if s > 0.2])
            bearish_news = len([s for s in sentiment_scores if s < -0.2])
            neutral_news = len(sentiment_scores) - bullish_news - bearish_news
            
            return {
                'overall_sentiment': overall_sentiment,
                'sentiment_score': avg_sentiment,
                'confidence': abs(avg_sentiment),
                'total_news': len(news_items),
                'bullish_news': bullish_news,
                'bearish_news': bearish_news,
                'neutral_news': neutral_news,
                'news_items': news_items[:5],  # Топ-5 новостей
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error("NewsParser", e, "_analyze_news_sentiment")
            return self._get_neutral_sentiment()
    
    def _is_cache_valid(self) -> bool:
        """Проверка валидности кэша"""
        if not self.last_update:
            return False
        
        # Кэш валиден 30 минут
        return datetime.now() - self.last_update < timedelta(minutes=30)
    
    def _get_neutral_sentiment(self) -> Dict:
        """Возвращает нейтральное настроение по умолчанию"""
        return {
            'overall_sentiment': 'Neutral',
            'sentiment_score': 0.0,
            'confidence': 0.0,
            'total_news': 0,
            'bullish_news': 0,
            'bearish_news': 0,
            'neutral_news': 0,
            'news_items': [],
            'last_updated': datetime.now().isoformat()
        }
    
    def get_trending_topics(self) -> List[str]:
        """Получение трендовых тем в криптоновостях"""
        try:
            # Получаем последние новости
            market_sentiment = self.get_market_sentiment(24)
            news_items = market_sentiment.get('news_items', [])
            
            if not news_items:
                return []
            
            # Извлекаем ключевые слова из заголовков
            all_text = ' '.join([item.get('title', '') for item in news_items])
            
            # Простой алгоритм извлечения трендовых тем
            # В реальном приложении можно использовать более сложные методы NLP
            
            crypto_keywords = [
                'bitcoin', 'btc', 'ethereum', 'eth', 'binance', 'bnb',
                'cardano', 'ada', 'ripple', 'xrp', 'solana', 'sol',
                'polkadot', 'dot', 'chainlink', 'link', 'defi', 'nft',
                'metaverse', 'web3', 'dao', 'staking', 'yield', 'mining'
            ]
            
            trending = []
            text_lower = all_text.lower()
            
            for keyword in crypto_keywords:
                count = text_lower.count(keyword)
                if count >= 2:  # Появляется минимум в 2 новостях
                    trending.append(keyword.upper())
            
            return trending[:10]  # Топ-10 трендов
            
        except Exception as e:
            log_error("NewsParser", e, "get_trending_topics")
            return []
    
    def get_fear_greed_index(self) -> Dict:
        """Получение индекса страха и жадности (симуляция)"""
        try:
            # В реальном приложении здесь будет API запрос к Alternative.me
            # Сейчас генерируем на основе анализа новостей
            
            sentiment_data = self.get_market_sentiment()
            sentiment_score = sentiment_data.get('sentiment_score', 0)
            
            # Конвертируем в индекс от 0 до 100
            # -1 (полный страх) -> 0, 0 (нейтральность) -> 50, 1 (полная жадность) -> 100
            fear_greed_value = max(0, min(100, 50 + (sentiment_score * 50)))
            
            # Определяем категорию
            if fear_greed_value <= 25:
                category = "Extreme Fear"
            elif fear_greed_value <= 45:
                category = "Fear"
            elif fear_greed_value <= 55:
                category = "Neutral"
            elif fear_greed_value <= 75:
                category = "Greed"
            else:
                category = "Extreme Greed"
            
            return {
                'value': int(fear_greed_value),
                'category': category,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error("NewsParser", e, "get_fear_greed_index")
            return {'value': 50, 'category': 'Neutral', 'timestamp': datetime.now().isoformat()}
