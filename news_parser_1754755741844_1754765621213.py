import requests
import feedparser
import trafilatura
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
import time
from utils.logger import get_logger, log_api_call

logger = get_logger(__name__)

class NewsParser:
    """Advanced news parser for cryptocurrency sentiment analysis"""
    
    def __init__(self):
        # RSS feeds for crypto news with backup sources
        self.rss_feeds = [
            "https://cointelegraph.com/rss",
            "https://coindesk.com/arc/outboundfeeds/rss/",
            "https://decrypt.co/feed",
            "https://www.coinbase.com/blog/rss.xml",
            "https://blog.binance.com/en/rss.xml",
            "https://bitcoinmagazine.com/.rss/full/",
            "https://www.newsbtc.com/feed/",
            "https://cryptonews.com/news/feed/",
            "https://beincrypto.com/feed/",
            "https://cryptoslate.com/feed/"
        ]
        
        # Enhanced keyword dictionaries for better sentiment analysis
        self.positive_keywords = [
            # Price action
            'bullish', 'surge', 'rally', 'gain', 'increase', 'rise', 'pump', 'moon', 'soar', 'spike',
            'breakthrough', 'breakout', 'upward', 'climb', 'bounce', 'recovery', 'rebound',
            
            # Market sentiment
            'optimistic', 'positive', 'confidence', 'enthusiasm', 'excitement', 'momentum',
            'strong', 'robust', 'healthy', 'solid', 'stable',
            
            # Adoption and partnerships
            'adoption', 'partnership', 'integration', 'collaboration', 'alliance', 'merger',
            'investment', 'funding', 'backing', 'support', 'endorsement',
            
            # Technical developments
            'upgrade', 'update', 'improvement', 'enhancement', 'innovation', 'development',
            'launch', 'release', 'milestone', 'achievement', 'success', 'breakthrough',
            
            # Institutional interest
            'institutional', 'corporate', 'enterprise', 'mainstream', 'traditional',
            'wall street', 'bank', 'financial institution'
        ]
        
        self.negative_keywords = [
            # Price action
            'bearish', 'crash', 'dump', 'decline', 'fall', 'drop', 'plunge', 'collapse', 'dip',
            'correction', 'selloff', 'slump', 'tumble', 'slide', 'downward', 'retreat',
            
            # Market sentiment
            'fear', 'uncertainty', 'doubt', 'panic', 'concern', 'worry', 'anxiety',
            'weak', 'unstable', 'volatile', 'risky', 'dangerous',
            
            # Regulatory and security
            'regulation', 'ban', 'restriction', 'prohibition', 'crackdown', 'investigation',
            'lawsuit', 'legal action', 'regulatory pressure', 'compliance',
            'hack', 'breach', 'scam', 'fraud', 'theft', 'exploit', 'vulnerability',
            
            # Market issues
            'manipulation', 'bubble', 'overvalued', 'speculation', 'warning', 'alert',
            'risk', 'threat', 'challenge', 'problem', 'issue', 'difficulty'
        ]
        
        # Symbol variations for better matching
        self.symbol_variations = {
            'BTC': ['bitcoin', 'btc', 'btcusdt'],
            'ETH': ['ethereum', 'eth', 'ethusdt', 'ether'],
            'BNB': ['binance coin', 'bnb', 'bnbusdt'],
            'ADA': ['cardano', 'ada', 'adausdt'],
            'DOT': ['polkadot', 'dot', 'dotusdt'],
            'SOL': ['solana', 'sol', 'solusdt'],
            'AVAX': ['avalanche', 'avax', 'avaxusdt'],
            'MATIC': ['polygon', 'matic', 'maticusdt'],
            'DOGE': ['dogecoin', 'doge', 'dogeusdt'],
            'XRP': ['ripple', 'xrp', 'xrpusdt']
        }
        
        # Cache for news data with TTL
        self.news_cache = {}
        self.cache_duration = 300  # 5 minutes
        
        # Request session for better performance
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        logger.info(f"Advanced News Parser initialized with {len(self.rss_feeds)} RSS feeds")
    
    def fetch_news_from_rss(self, max_articles: int = 100) -> List[Dict]:
        """Fetch news from RSS feeds with error handling and rate limiting"""
        all_articles = []
        
        for feed_url in self.rss_feeds:
            try:
                start_time = time.time()
                logger.info(f"Fetching news from: {feed_url}")
                
                # Parse RSS feed with timeout
                feed = feedparser.parse(feed_url)
                response_time = time.time() - start_time
                
                if hasattr(feed, 'status') and feed.status != 200:
                    log_api_call("RSS", feed_url, False, response_time, f"HTTP {feed.status}")
                    continue
                
                log_api_call("RSS", feed_url, True, response_time)
                
                if feed.entries:
                    articles_processed = 0
                    for entry in feed.entries:
                        if articles_processed >= 15:  # Limit per feed
                            break
                            
                        try:
                            # Parse publication date with multiple formats
                            pub_date = self._parse_publication_date(entry)
                            
                            # Only include recent articles (last 48 hours)
                            if pub_date and pub_date > datetime.now() - timedelta(hours=48):
                                article = {
                                    'title': entry.get('title', '').strip(),
                                    'summary': entry.get('summary', '').strip(),
                                    'link': entry.get('link', '').strip(),
                                    'published': pub_date,
                                    'source': self._extract_domain(feed_url),
                                    'feed_url': feed_url
                                }
                                
                                # Skip if title or link is missing
                                if not article['title'] or not article['link']:
                                    continue
                                
                                # Get full content if possible (with rate limiting)
                                if len(all_articles) < 50:  # Only get full content for first 50 articles
                                    content = self._extract_article_content(article['link'])
                                    if content:
                                        article['content'] = content
                                
                                all_articles.append(article)
                                articles_processed += 1
                                
                        except Exception as e:
                            logger.warning(f"Error processing article from {feed_url}: {str(e)}")
                            continue
                
                # Rate limiting between feeds
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching from {feed_url}: {str(e)}")
                log_api_call("RSS", feed_url, False, 0, str(e))
                continue
        
        # Remove duplicates based on title similarity
        unique_articles = self._remove_duplicate_articles(all_articles)
        
        # Sort by publication date (newest first)
        unique_articles.sort(key=lambda x: x['published'] if x['published'] else datetime.min, reverse=True)
        
        logger.info(f"Fetched {len(unique_articles)} unique articles from {len(self.rss_feeds)} RSS feeds")
        return unique_articles[:max_articles]
    
    def _parse_publication_date(self, entry) -> Optional[datetime]:
        """Parse publication date with multiple fallback methods"""
        try:
            # Try published_parsed first
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            
            # Try updated_parsed
            if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
            
            # Try to parse published string
            if hasattr(entry, 'published') and entry.published:
                # Common date formats
                date_formats = [
                    '%a, %d %b %Y %H:%M:%S %z',
                    '%a, %d %b %Y %H:%M:%S %Z',
                    '%Y-%m-%dT%H:%M:%S%z',
                    '%Y-%m-%d %H:%M:%S'
                ]
                
                for date_format in date_formats:
                    try:
                        return datetime.strptime(entry.published, date_format).replace(tzinfo=None)
                    except:
                        continue
            
            # Default to current time if no date found
            return datetime.now()
            
        except Exception as e:
            logger.warning(f"Error parsing publication date: {str(e)}")
            return datetime.now()
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL"""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace('www.', '')
        except:
            return url
    
    def _remove_duplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on title similarity"""
        unique_articles = []
        seen_titles = set()
        
        for article in articles:
            title = article.get('title', '').lower().strip()
            
            # Skip if title is too short or empty
            if len(title) < 10:
                continue
            
            # Simple deduplication based on title similarity
            is_duplicate = False
            title_words = set(title.split())
            
            for seen_title in seen_titles:
                seen_words = set(seen_title.split())
                
                # Calculate Jaccard similarity
                intersection = len(title_words.intersection(seen_words))
                union = len(title_words.union(seen_words))
                
                if union > 0 and intersection / union > 0.7:  # 70% similarity threshold
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_articles.append(article)
                seen_titles.add(title)
        
        return unique_articles
    
    def _extract_article_content(self, url: str) -> str:
        """Extract full article content using trafilatura with error handling"""
        try:
            if not url or not url.startswith('http'):
                return ""
            
            start_time = time.time()
            
            # Download the webpage with timeout
            downloaded = trafilatura.fetch_url(url, timeout=10)
            if not downloaded:
                return ""
            
            # Extract text content
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            
            response_time = time.time() - start_time
            log_api_call("Trafilatura", url, bool(text), response_time)
            
            return text if text else ""
            
        except Exception as e:
            logger.warning(f"Error extracting content from {url}: {str(e)}")
            log_api_call("Trafilatura", url, False, 0, str(e))
            return ""
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Enhanced sentiment analysis using keyword-based approach with weighting"""
        try:
            if not text:
                return {'sentiment_score': 0.0, 'confidence': 0.0}
            
            text_lower = text.lower()
            text_words = text_lower.split()
            
            # Count positive and negative keywords with context weighting
            positive_score = 0
            negative_score = 0
            total_matches = 0
            
            # Analyze positive keywords
            for keyword in self.positive_keywords:
                if keyword in text_lower:
                    # Weight by keyword importance and frequency
                    frequency = text_lower.count(keyword)
                    weight = self._get_keyword_weight(keyword)
                    positive_score += frequency * weight
                    total_matches += frequency
            
            # Analyze negative keywords
            for keyword in self.negative_keywords:
                if keyword in text_lower:
                    frequency = text_lower.count(keyword)
                    weight = self._get_keyword_weight(keyword)
                    negative_score += frequency * weight
                    total_matches += frequency
            
            # Handle negation (simple approach)
            negation_words = ['not', 'no', 'never', 'don\'t', 'doesn\'t', 'won\'t', 'can\'t']
            negation_boost = 1.0
            
            for negation in negation_words:
                if negation in text_lower:
                    negation_boost *= 1.2  # Increase uncertainty due to negation
            
            if total_matches == 0:
                return {'sentiment_score': 0.0, 'confidence': 0.0}
            
            # Calculate sentiment score (-1 to 1)
            raw_score = (positive_score - negative_score) / (positive_score + negative_score)
            
            # Apply negation adjustment
            sentiment_score = raw_score / negation_boost
            
            # Calculate confidence based on number of sentiment words and text length
            text_length = len(text_words)
            confidence = min(1.0, (total_matches / max(text_length / 50, 1)) * 0.5)
            confidence = max(0.1, confidence)  # Minimum confidence
            
            return {
                'sentiment_score': sentiment_score,
                'confidence': confidence,
                'positive_matches': positive_score,
                'negative_matches': negative_score,
                'total_matches': total_matches
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {'sentiment_score': 0.0, 'confidence': 0.0}
    
    def _get_keyword_weight(self, keyword: str) -> float:
        """Get weight for keyword based on importance"""
        # High impact keywords
        high_impact = ['crash', 'surge', 'ban', 'adoption', 'partnership', 'regulation']
        
        # Medium impact keywords
        medium_impact = ['bullish', 'bearish', 'rise', 'fall', 'increase', 'decrease']
        
        if keyword in high_impact:
            return 2.0
        elif keyword in medium_impact:
            return 1.5
        else:
            return 1.0
    
    def get_market_sentiment(self) -> Dict:
        """Get overall market sentiment from recent news with enhanced analysis"""
        try:
            # Check cache first
            cache_key = 'market_sentiment'
            if cache_key in self.news_cache:
                cached_data = self.news_cache[cache_key]
                if time.time() - cached_data['timestamp'] < self.cache_duration:
                    return cached_data['data']
            
            # Fetch fresh news
            articles = self.fetch_news_from_rss(50)
            
            if not articles:
                return {
                    'overall_sentiment': 'Neutral',
                    'sentiment_score': 0.0,
                    'confidence': 0.0,
                    'articles_analyzed': 0
                }
            
            sentiment_scores = []
            confidences = []
            source_weights = {}
            
            # Calculate source reliability weights
            for article in articles:
                source = article.get('source', 'unknown')
                source_weights[source] = source_weights.get(source, 0) + 1
            
            # Analyze each article
            for article in articles:
                try:
                    # Combine title, summary, and content for analysis
                    text_parts = []
                    
                    if article.get('title'):
                        text_parts.append(article['title'] * 2)  # Weight title more
                    
                    if article.get('summary'):
                        text_parts.append(article['summary'])
                    
                    if article.get('content'):
                        # Limit content length to avoid overwhelming with less relevant text
                        content = article['content'][:1000]
                        text_parts.append(content)
                    
                    text_to_analyze = ' '.join(text_parts)
                    
                    if len(text_to_analyze.strip()) < 20:  # Skip very short texts
                        continue
                    
                    sentiment_result = self.analyze_sentiment(text_to_analyze)
                    
                    if sentiment_result['confidence'] > 0.15:  # Minimum confidence threshold
                        # Apply source weight
                        source = article.get('source', 'unknown')
                        source_weight = min(2.0, source_weights.get(source, 1) / 5.0 + 0.5)
                        
                        weighted_confidence = sentiment_result['confidence'] * source_weight
                        
                        sentiment_scores.append(sentiment_result['sentiment_score'])
                        confidences.append(weighted_confidence)
                
                except Exception as e:
                    logger.warning(f"Error analyzing article sentiment: {str(e)}")
                    continue
            
            if not sentiment_scores:
                result = {
                    'overall_sentiment': 'Neutral',
                    'sentiment_score': 0.0,
                    'confidence': 0.0,
                    'articles_analyzed': 0
                }
            else:
                # Calculate weighted average sentiment
                total_weight = sum(confidences)
                if total_weight > 0:
                    weighted_scores = [score * conf for score, conf in zip(sentiment_scores, confidences)]
                    avg_sentiment = sum(weighted_scores) / total_weight
                else:
                    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                # Determine overall sentiment with more nuanced thresholds
                if avg_sentiment > 0.2:
                    overall_sentiment = 'Bullish'
                elif avg_sentiment > 0.05:
                    overall_sentiment = 'Slightly Bullish'
                elif avg_sentiment < -0.2:
                    overall_sentiment = 'Bearish'
                elif avg_sentiment < -0.05:
                    overall_sentiment = 'Slightly Bearish'
                else:
                    overall_sentiment = 'Neutral'
                
                result = {
                    'overall_sentiment': overall_sentiment,
                    'sentiment_score': avg_sentiment,
                    'confidence': avg_confidence,
                    'articles_analyzed': len(sentiment_scores),
                    'total_articles_fetched': len(articles),
                    'positive_articles': len([s for s in sentiment_scores if s > 0.1]),
                    'negative_articles': len([s for s in sentiment_scores if s < -0.1]),
                    'neutral_articles': len([s for s in sentiment_scores if -0.1 <= s <= 0.1]),
                    'sources_analyzed': len(source_weights)
                }
            
            # Cache the result
            self.news_cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
            
            logger.info(f"Market sentiment analysis: {result['overall_sentiment']} "
                       f"(Score: {result['sentiment_score']:.3f}, "
                       f"Confidence: {result['confidence']:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"Error getting market sentiment: {str(e)}")
            return {
                'overall_sentiment': 'Unknown',
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'articles_analyzed': 0,
                'error': str(e)
            }
    
    def analyze_symbol_sentiment(self, symbol: str) -> Optional[Dict]:
        """Analyze sentiment for a specific cryptocurrency symbol with enhanced matching"""
        try:
            # Check cache first
            cache_key = f'symbol_sentiment_{symbol}'
            if cache_key in self.news_cache:
                cached_data = self.news_cache[cache_key]
                if time.time() - cached_data['timestamp'] < self.cache_duration:
                    return cached_data['data']
            
            # Fetch news articles
            articles = self.fetch_news_from_rss(100)
            
            if not articles:
                return None
            
            # Get symbol variations for better matching
            symbol_clean = symbol.replace('USDT', '').replace('BTC', '').replace('ETH', '').upper()
            variations = self.symbol_variations.get(symbol_clean, [symbol_clean.lower()])
            variations.extend([symbol.lower(), symbol_clean.lower()])
            
            # Filter articles mentioning the symbol
            symbol_articles = []
            
            for article in articles:
                text_to_search = ' '.join([
                    article.get('title', '').lower(),
                    article.get('summary', '').lower(),
                    article.get('content', '').lower()[:500]  # First 500 chars of content
                ])
                
                # Check if any variation of the symbol is mentioned
                symbol_mentioned = False
                mention_count = 0
                
                for variation in variations:
                    if variation and len(variation) > 1:
                        # Use word boundaries to avoid partial matches
                        pattern = r'\b' + re.escape(variation) + r'\b'
                        matches = len(re.findall(pattern, text_to_search, re.IGNORECASE))
                        
                        if matches > 0:
                            symbol_mentioned = True
                            mention_count += matches
                
                if symbol_mentioned:
                    article['mention_count'] = mention_count
                    symbol_articles.append(article)
            
            if not symbol_articles:
                return None
            
            # Analyze sentiment of symbol-specific articles
            sentiment_scores = []
            confidences = []
            
            for article in symbol_articles:
                try:
                    # Create text for analysis with emphasis on symbol context
                    text_parts = []
                    
                    if article.get('title'):
                        text_parts.append(article['title'] * 3)  # Title gets highest weight
                    
                    if article.get('summary'):
                        text_parts.append(article['summary'] * 2)
                    
                    if article.get('content'):
                        # Focus on first part of content
                        content = article['content'][:800]
                        text_parts.append(content)
                    
                    text_to_analyze = ' '.join(text_parts)
                    sentiment_result = self.analyze_sentiment(text_to_analyze)
                    
                    if sentiment_result['confidence'] > 0.1:
                        # Weight by mention frequency
                        mention_weight = min(2.0, article.get('mention_count', 1) / 3.0 + 0.5)
                        adjusted_confidence = sentiment_result['confidence'] * mention_weight
                        
                        sentiment_scores.append(sentiment_result['sentiment_score'])
                        confidences.append(adjusted_confidence)
                
                except Exception as e:
                    logger.warning(f"Error analyzing symbol article sentiment: {str(e)}")
                    continue
            
            if not sentiment_scores:
                return None
            
            # Calculate weighted average
            total_weight = sum(confidences)
            if total_weight > 0:
                weighted_scores = [score * conf for score, conf in zip(sentiment_scores, confidences)]
                avg_sentiment = sum(weighted_scores) / total_weight
            else:
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            
            avg_confidence = sum(confidences) / len(confidences)
            
            # Determine sentiment category
            if avg_sentiment > 0.15:
                sentiment = 'Bullish'
            elif avg_sentiment > 0.05:
                sentiment = 'Slightly Bullish'
            elif avg_sentiment < -0.15:
                sentiment = 'Bearish'
            elif avg_sentiment < -0.05:
                sentiment = 'Slightly Bearish'
            else:
                sentiment = 'Neutral'
            
            result = {
                'symbol': symbol,
                'sentiment': sentiment,
                'sentiment_score': avg_sentiment,
                'confidence': avg_confidence,
                'articles_mentioning': len(symbol_articles),
                'total_articles_scanned': len(articles),
                'positive_mentions': len([s for s in sentiment_scores if s > 0.1]),
                'negative_mentions': len([s for s in sentiment_scores if s < -0.1]),
                'neutral_mentions': len([s for s in sentiment_scores if -0.1 <= s <= 0.1]),
                'analysis_time': datetime.now()
            }
            
            # Cache the result
            self.news_cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
            
            logger.info(f"Symbol sentiment analysis for {symbol}: {sentiment} "
                       f"(Score: {avg_sentiment:.3f}, Articles: {len(symbol_articles)})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing symbol sentiment for {symbol}: {str(e)}")
            return None
    
    def get_trending_topics(self, limit: int = 10) -> List[Dict]:
        """Extract trending topics from news headlines"""
        try:
            articles = self.fetch_news_from_rss(50)
            
            if not articles:
                return []
            
            # Extract keywords from titles
            word_frequency = {}
            
            # Common words to exclude
            stopwords = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
                'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
                'above', 'below', 'between', 'among', 'throughout', 'despite', 'towards', 'upon',
                'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
                'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
                'crypto', 'cryptocurrency', 'bitcoin', 'news', 'today', 'new', 'latest'
            }
            
            for article in articles:
                title = article.get('title', '').lower()
                words = re.findall(r'\b\w+\b', title)
                
                for word in words:
                    if len(word) > 3 and word not in stopwords:
                        word_frequency[word] = word_frequency.get(word, 0) + 1
            
            # Sort by frequency and create trending topics
            trending = sorted(word_frequency.items(), key=lambda x: x[1], reverse=True)
            
            topics = []
            for word, count in trending[:limit]:
                if count > 1:  # Only include words mentioned multiple times
                    topics.append({
                        'topic': word.title(),
                        'mentions': count,
                        'trend_score': count / len(articles)
                    })
            
            return topics
            
        except Exception as e:
            logger.error(f"Error extracting trending topics: {str(e)}")
            return []
    
    def cleanup_cache(self):
        """Clean up expired cache entries"""
        try:
            current_time = time.time()
            expired_keys = []
            
            for key, data in self.news_cache.items():
                if current_time - data['timestamp'] > self.cache_duration:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.news_cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up cache: {str(e)}")

