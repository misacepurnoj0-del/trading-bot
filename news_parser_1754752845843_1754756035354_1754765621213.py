import requests
import feedparser
import trafilatura
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
import time
from utils.logger import get_logger

logger = get_logger(__name__)

class NewsParser:
    """News parser for cryptocurrency sentiment analysis"""
    
    def __init__(self):
        # RSS feeds for crypto news
        self.rss_feeds = [
            "https://cointelegraph.com/rss",
            "https://coindesk.com/arc/outboundfeeds/rss/",
            "https://decrypt.co/feed",
            "https://www.coinbase.com/blog/rss.xml",
            "https://blog.binance.com/en/rss.xml",
            "https://bitcoinmagazine.com/.rss/full/"
        ]
        
        # Keywords for sentiment analysis
        self.positive_keywords = [
            'bullish', 'surge', 'rally', 'gain', 'increase', 'rise', 'pump', 'moon',
            'breakthrough', 'adoption', 'partnership', 'integration', 'upgrade',
            'positive', 'optimistic', 'growth', 'expansion', 'launch', 'success'
        ]
        
        self.negative_keywords = [
            'bearish', 'crash', 'dump', 'decline', 'fall', 'drop', 'plunge',
            'fear', 'uncertainty', 'doubt', 'hack', 'scam', 'regulation',
            'ban', 'restriction', 'concern', 'warning', 'risk', 'volatility'
        ]
        
        # Cache for news data
        self.news_cache = {}
        self.cache_duration = 300  # 5 minutes
        
        logger.info("News Parser initialized with 6 RSS feeds")
    
    def fetch_news_from_rss(self, max_articles: int = 50) -> List[Dict]:
        """Fetch news from RSS feeds"""
        all_articles = []
        
        for feed_url in self.rss_feeds:
            try:
                logger.info(f"Fetching news from: {feed_url}")
                
                # Parse RSS feed
                feed = feedparser.parse(feed_url)
                
                if feed.entries:
                    for entry in feed.entries[:10]:  # Limit per feed
                        try:
                            # Parse publication date
                            pub_date = datetime.now()
                            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                pub_date = datetime(*entry.published_parsed[:6])
                            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                                pub_date = datetime(*entry.updated_parsed[:6])
                            
                            # Only include recent articles (last 24 hours)
                            if pub_date > datetime.now() - timedelta(hours=24):
                                article = {
                                    'title': entry.get('title', ''),
                                    'summary': entry.get('summary', ''),
                                    'link': entry.get('link', ''),
                                    'published': pub_date,
                                    'source': feed_url
                                }
                                
                                # Get full content if possible
                                content = self._extract_article_content(entry.get('link', ''))
                                if content:
                                    article['content'] = content
                                
                                all_articles.append(article)
                                
                        except Exception as e:
                            logger.warning(f"Error processing article from {feed_url}: {str(e)}")
                            continue
                
                # Small delay between feeds
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching from {feed_url}: {str(e)}")
                continue
        
        # Sort by publication date (newest first)
        all_articles.sort(key=lambda x: x['published'], reverse=True)
        
        logger.info(f"Fetched {len(all_articles)} articles from RSS feeds")
        return all_articles[:max_articles]
    
    def _extract_article_content(self, url: str) -> str:
        """Extract full article content using trafilatura"""
        try:
            if not url:
                return ""
            
            # Download the webpage
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return ""
            
            # Extract text content
            text = trafilatura.extract(downloaded)
            return text if text else ""
            
        except Exception as e:
            logger.warning(f"Error extracting content from {url}: {str(e)}")
            return ""
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text using keyword-based approach"""
        try:
            if not text:
                return {'sentiment_score': 0.0, 'confidence': 0.0}
            
            text_lower = text.lower()
            
            # Count positive and negative keywords
            positive_count = sum(1 for keyword in self.positive_keywords if keyword in text_lower)
            negative_count = sum(1 for keyword in self.negative_keywords if keyword in text_lower)
            
            total_sentiment_words = positive_count + negative_count
            
            if total_sentiment_words == 0:
                return {'sentiment_score': 0.0, 'confidence': 0.0}
            
            # Calculate sentiment score (-1 to 1)
            sentiment_score = (positive_count - negative_count) / total_sentiment_words
            
            # Calculate confidence based on number of sentiment words
            confidence = min(1.0, total_sentiment_words / 10.0)
            
            return {
                'sentiment_score': sentiment_score,
                'confidence': confidence,
                'positive_words': positive_count,
                'negative_words': negative_count
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {'sentiment_score': 0.0, 'confidence': 0.0}
    
    def get_market_sentiment(self) -> Dict:
        """Get overall market sentiment from recent news"""
        try:
            # Check cache first
            cache_key = 'market_sentiment'
            if cache_key in self.news_cache:
                cached_data = self.news_cache[cache_key]
                if time.time() - cached_data['timestamp'] < self.cache_duration:
                    return cached_data['data']
            
            # Fetch fresh news
            articles = self.fetch_news_from_rss(30)
            
            if not articles:
                return {
                    'overall_sentiment': 'Neutral',
                    'sentiment_score': 0.0,
                    'confidence': 0.0,
                    'articles_analyzed': 0
                }
            
            sentiment_scores = []
            confidences = []
            
            for article in articles:
                # Combine title, summary, and content for analysis
                text_to_analyze = f"{article.get('title', '')} {article.get('summary', '')} {article.get('content', '')}"
                
                sentiment_result = self.analyze_sentiment(text_to_analyze)
                
                if sentiment_result['confidence'] > 0.1:  # Only include if reasonably confident
                    sentiment_scores.append(sentiment_result['sentiment_score'])
                    confidences.append(sentiment_result['confidence'])
            
            if not sentiment_scores:
                result = {
                    'overall_sentiment': 'Neutral',
                    'sentiment_score': 0.0,
                    'confidence': 0.0,
                    'articles_analyzed': 0
                }
            else:
                # Calculate weighted average sentiment
                weighted_scores = [score * conf for score, conf in zip(sentiment_scores, confidences)]
                total_weight = sum(confidences)
                
                avg_sentiment = sum(weighted_scores) / total_weight if total_weight > 0 else 0.0
                avg_confidence = sum(confidences) / len(confidences)
                
                # Determine overall sentiment
                if avg_sentiment > 0.1:
                    overall_sentiment = 'Bullish'
                elif avg_sentiment < -0.1:
                    overall_sentiment = 'Bearish'
                else:
                    overall_sentiment = 'Neutral'
                
                result = {
                    'overall_sentiment': overall_sentiment,
                    'sentiment_score': avg_sentiment,
                    'confidence': avg_confidence,
                    'articles_analyzed': len(sentiment_scores),
                    'positive_articles': len([s for s in sentiment_scores if s > 0.1]),
                    'negative_articles': len([s for s in sentiment_scores if s < -0.1]),
                    'neutral_articles': len([s for s in sentiment_scores if -0.1 <= s <= 0.1])
                }
            
            # Cache the result
            self.news_cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
            
            logger.info(f"Market sentiment analysis: {result['overall_sentiment']} ({result['sentiment_score']:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error getting market sentiment: {str(e)}")
            return {
                'overall_sentiment': 'Unknown',
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'articles_analyzed': 0
            }
    
    def analyze_symbol_sentiment(self, symbol: str) -> Optional[Dict]:
        """Analyze sentiment for a specific cryptocurrency symbol"""
        try:
            # Check cache first
            cache_key = f'symbol_sentiment_{symbol}'
            if cache_key in self.news_cache:
                cached_data = self.news_cache[cache_key]
                if time.time() - cached_data['timestamp'] < self.cache_duration:
                    return cached_data['data']
            
            # Fetch news articles
            articles = self.fetch_news_from_rss(50)
            
            # Filter articles mentioning the symbol
            symbol_articles = []
            symbol_variations = [
                symbol.lower(),
                symbol.upper(),
                symbol.replace('USDT', '').lower(),
                symbol.replace('BTC', '').lower()
            ]
            
            for article in articles:
                text_to_search = f"{article.get('title', '')} {article.get('summary', '')} {article.get('content', '')}".lower()
                
                # Check if any variation of the symbol is mentioned
                if any(variation in text_to_search for variation in symbol_variations if variation):
                    symbol_articles.append(article)
            
            if not symbol_articles:
                return None
            
            # Analyze sentiment of symbol-specific articles
            sentiment_scores = []
            confidences = []
            
            for article in symbol_articles:
                text_to_analyze = f"{article.get('title', '')} {article.get('summary', '')} {article.get('content', '')}"
                sentiment_result = self.analyze_sentiment(text_to_analyze)
                
                if sentiment_result['confidence'] > 0.1:
                    sentiment_scores.append(sentiment_result['sentiment_score'])
                    confidences.append(sentiment_result['confidence'])
            
            if not sentiment_scores:
                return None
            
            # Calculate weighted average
            weighted_scores = [score * conf for score, conf in zip(sentiment_scores, confidences)]
            total_weight = sum(confidences)
            
            avg_sentiment = sum(weighted_scores) / total_weight if total_weight > 0 else 0.0
            avg_confidence = sum(confidences) / len(confidences)
            
            # Determine sentiment
            if avg_sentiment > 0.1:
                sentiment = 'Bullish'
            elif avg_sentiment < -0.1:
                sentiment = 'Bearish'
            else:
                sentiment = 'Neutral'
            
            result = {
                'symbol': symbol,
                'sentiment': sentiment,
                'sentiment_score': avg_sentiment,
                'confidence': avg_confidence,
                'articles_found': len(symbol_articles),
                'articles_analyzed': len(sentiment_scores)
            }
            
            # Cache the result
            self.news_cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
            
            logger.info(f"Symbol {symbol} sentiment: {sentiment} ({avg_sentiment:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing symbol sentiment for {symbol}: {str(e)}")
            return None
    
    def get_latest_headlines(self, limit: int = 10) -> List[Dict]:
        """Get latest crypto news headlines"""
        try:
            articles = self.fetch_news_from_rss(limit * 2)
            
            headlines = []
            for article in articles[:limit]:
                sentiment_result = self.analyze_sentiment(article.get('title', '') + ' ' + article.get('summary', ''))
                
                headlines.append({
                    'title': article.get('title', ''),
                    'summary': article.get('summary', '')[:200] + '...' if len(article.get('summary', '')) > 200 else article.get('summary', ''),
                    'link': article.get('link', ''),
                    'published': article.get('published', datetime.now()).strftime('%Y-%m-%d %H:%M'),
                    'sentiment': 'Positive' if sentiment_result['sentiment_score'] > 0.1 else 'Negative' if sentiment_result['sentiment_score'] < -0.1 else 'Neutral',
                    'sentiment_score': sentiment_result['sentiment_score']
                })
            
            return headlines
            
        except Exception as e:
            logger.error(f"Error getting latest headlines: {str(e)}")
            return []
    
    def clear_cache(self):
        """Clear the news cache"""
        self.news_cache.clear()
        logger.info("News cache cleared")
    
    def get_news_summary(self) -> Dict:
        """Get a summary of recent news analysis"""
        try:
            market_sentiment = self.get_market_sentiment()
            headlines = self.get_latest_headlines(5)
            
            return {
                'market_sentiment': market_sentiment,
                'latest_headlines': headlines,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sources_count': len(self.rss_feeds)
            }
            
        except Exception as e:
            logger.error(f"Error getting news summary: {str(e)}")
            return {
                'market_sentiment': {'overall_sentiment': 'Unknown', 'sentiment_score': 0.0},
                'latest_headlines': [],
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sources_count': 0
            }
