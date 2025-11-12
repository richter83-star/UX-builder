import tweepy
import praw
from textblob import TextBlob
import requests
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import re
import numpy as np
from collections import defaultdict
from loguru import logger

from app.utils.config import settings
from app.models.enums import MarketCategory, AnalyzerType

class SentimentAnalyzer:
    """
    Sentiment analysis engine that aggregates sentiment data from multiple sources
    including Twitter, Reddit, and news sources to provide market sentiment signals.
    """

    def __init__(self):
        self.twitter_client = None
        self.reddit_client = None
        self.news_api_key = settings.NEWS_API_KEY

        # Initialize Twitter client if credentials are available
        if all([settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET,
                settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET]):
            try:
                auth = tweepy.OAuthHandler(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET)
                auth.set_access_token(settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)
                self.twitter_client = tweepy.API(auth, wait_on_rate_limit=True)
                logger.info("Twitter client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Twitter client: {str(e)}")

        # Initialize Reddit client if credentials are available
        if all([settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET]):
            try:
                self.reddit_client = praw.Reddit(
                    client_id=settings.REDDIT_CLIENT_ID,
                    client_secret=settings.REDDIT_CLIENT_SECRET,
                    user_agent=settings.REDDIT_USER_AGENT
                )
                logger.info("Reddit client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Reddit client: {str(e)}")

        # Sentiment weighting for different sources
        self.source_weights = {
            'twitter': 0.4,
            'reddit': 0.3,
            'news': 0.3
        }

        # Cache for sentiment data to avoid redundant API calls
        self.sentiment_cache = {}
        self.cache_ttl = 300  # 5 minutes

    def _get_cache_key(self, keyword: str, source: str) -> str:
        """Generate cache key for sentiment data"""
        return f"{source}:{keyword}:{int(datetime.utcnow().timestamp() / self.cache_ttl)}"

    def _get_cached_sentiment(self, keyword: str, source: str) -> Optional[float]:
        """Get cached sentiment data if available"""
        cache_key = self._get_cache_key(keyword, source)
        return self.sentiment_cache.get(cache_key)

    def _cache_sentiment(self, keyword: str, source: str, sentiment: float):
        """Cache sentiment data"""
        cache_key = self._get_cache_key(keyword, source)
        self.sentiment_cache[cache_key] = sentiment

    def _extract_keywords_from_market(self, market_title: str, market_subtitle: str = "") -> List[str]:
        """Extract relevant keywords from market title and subtitle"""
        text = f"{market_title} {market_subtitle}".lower()

        # Remove common stop words and special characters
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'will', 'would', 'could', 'should'}
        words = re.findall(r'\b[a-z]+\b', text)
        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        # Add category-specific keywords
        category_keywords = []
        if any(word in text for word in ['election', 'president', 'congress', 'vote']):
            category_keywords.extend(['election', 'president', 'congress', 'politics', 'vote'])
        elif any(word in text for word in ['stock', 'market', 'economy', 'fed']):
            category_keywords.extend(['stock', 'market', 'economy', 'federal reserve', 'inflation'])
        elif any(word in text for word in ['game', 'team', 'player', 'sport']):
            category_keywords.extend(['game', 'team', 'player', 'sport'])

        return list(set(keywords + category_keywords))[:10]  # Limit to 10 keywords

    def _analyze_text_sentiment(self, text: str) -> float:
        """Analyze sentiment of a single text using TextBlob"""
        try:
            blob = TextBlob(text)
            # Normalize sentiment to -1 to 1 scale
            return blob.sentiment.polarity
        except Exception as e:
            logger.warning(f"Error analyzing text sentiment: {str(e)}")
            return 0.0

    async def _get_twitter_sentiment(self, keywords: List[str]) -> float:
        """Get sentiment from Twitter based on keywords"""
        if not self.twitter_client:
            return 0.0

        sentiments = []
        try:
            # Search for tweets containing keywords
            for keyword in keywords[:5]:  # Limit to avoid rate limits
                cached_sentiment = self._get_cached_sentiment(keyword, 'twitter')
                if cached_sentiment is not None:
                    sentiments.append(cached_sentiment)
                    continue

                try:
                    tweets = tweepy.Cursor(
                        self.twitter_client.search_tweets,
                        q=keyword,
                        lang='en',
                        tweet_mode='extended',
                        result_type='recent'
                    ).items(100)

                    keyword_sentiments = []
                    for tweet in tweets:
                        if tweet.full_text:
                            sentiment = self._analyze_text_sentiment(tweet.full_text)
                            keyword_sentiments.append(sentiment)

                    if keyword_sentiments:
                        avg_sentiment = np.mean(keyword_sentiments)
                        sentiments.append(avg_sentiment)
                        self._cache_sentiment(keyword, 'twitter', avg_sentiment)

                except tweepy.TweepyException as e:
                    logger.warning(f"Twitter API error for keyword '{keyword}': {str(e)}")
                    continue

                # Add delay between requests to respect rate limits
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error fetching Twitter sentiment: {str(e)}")
            return 0.0

        return np.mean(sentiments) if sentiments else 0.0

    async def _get_reddit_sentiment(self, keywords: List[str]) -> float:
        """Get sentiment from Reddit based on keywords"""
        if not self.reddit_client:
            return 0.0

        sentiments = []
        try:
            # Search relevant subreddits based on keywords
            subreddits = ['politics', 'news', 'worldnews', 'business', 'stocks', 'sports', 'technology']

            for keyword in keywords[:3]:  # Limit to avoid rate limits
                cached_sentiment = self._get_cached_sentiment(keyword, 'reddit')
                if cached_sentiment is not None:
                    sentiments.append(cached_sentiment)
                    continue

                keyword_sentiments = []
                for subreddit_name in subreddits:
                    try:
                        subreddit = self.reddit_client.subreddit(subreddit_name)

                        # Search for posts in the last week
                        for submission in subreddit.search(keyword, sort='hot', time_filter='week', limit=20):
                            # Analyze title and comments
                            title_sentiment = self._analyze_text_sentiment(submission.title)
                            keyword_sentiments.append(title_sentiment)

                            # Get top comments
                            submission.comments.replace_more(limit=0)
                            for comment in submission.comments[:10]:
                                if hasattr(comment, 'body'):
                                    comment_sentiment = self._analyze_text_sentiment(comment.body)
                                    keyword_sentiments.append(comment_sentiment)

                    except Exception as e:
                        logger.debug(f"Reddit error in r/{subreddit_name} for keyword '{keyword}': {str(e)}")
                        continue

                if keyword_sentiments:
                    avg_sentiment = np.mean(keyword_sentiments)
                    sentiments.append(avg_sentiment)
                    self._cache_sentiment(keyword, 'reddit', avg_sentiment)

                # Add delay between requests
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error fetching Reddit sentiment: {str(e)}")
            return 0.0

        return np.mean(sentiments) if sentiments else 0.0

    async def _get_news_sentiment(self, keywords: List[str]) -> float:
        """Get sentiment from news sources based on keywords"""
        if not self.news_api_key:
            return 0.0

        sentiments = []
        try:
            base_url = "https://newsapi.org/v2/everything"

            for keyword in keywords[:3]:  # Limit to avoid rate limits
                cached_sentiment = self._get_cached_sentiment(keyword, 'news')
                if cached_sentiment is not None:
                    sentiments.append(cached_sentiment)
                    continue

                params = {
                    'q': keyword,
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'pageSize': 50,
                    'apiKey': self.news_api_key
                }

                try:
                    response = requests.get(base_url, params=params, timeout=10)
                    if response.status_code == 200:
                        articles = response.json().get('articles', [])
                        keyword_sentiments = []

                        for article in articles:
                            title = article.get('title', '')
                            description = article.get('description', '')
                            content = article.get('content', '')

                            # Analyze title and description
                            if title:
                                title_sentiment = self._analyze_text_sentiment(title)
                                keyword_sentiments.append(title_sentiment)

                            if description:
                                desc_sentiment = self._analyze_text_sentiment(description)
                                keyword_sentiments.append(desc_sentiment)

                            if content:
                                content_sentiment = self._analyze_text_sentiment(content)
                                keyword_sentiments.append(content_sentiment)

                        if keyword_sentiments:
                            avg_sentiment = np.mean(keyword_sentiments)
                            sentiments.append(avg_sentiment)
                            self._cache_sentiment(keyword, 'news', avg_sentiment)

                except Exception as e:
                    logger.warning(f"News API error for keyword '{keyword}': {str(e)}")
                    continue

                # Add delay between requests
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error fetching news sentiment: {str(e)}")
            return 0.0

        return np.mean(sentiments) if sentiments else 0.0

    def _calculate_trend_score(self, sentiment_history: List[float]) -> float:
        """Calculate trend score from sentiment history"""
        if len(sentiment_history) < 2:
            return 0.0

        try:
            # Calculate linear trend using least squares
            x = np.arange(len(sentiment_history))
            y = np.array(sentiment_history)

            # Calculate slope (trend)
            slope = np.polyfit(x, y, 1)[0]

            # Normalize trend to -1 to 1 scale
            return np.tanh(slope * 10)  # Using tanh for smooth normalization

        except Exception as e:
            logger.warning(f"Error calculating trend score: {str(e)}")
            return 0.0

    def _calculate_confidence(self, sentiment_scores: Dict[str, float],
                            sentiment_volatility: float) -> float:
        """Calculate confidence score for sentiment analysis"""
        try:
            # Base confidence from number of sources
            source_confidence = min(len(sentiment_scores) * 20, 60)  # Max 60 from sources

            # Confidence from consistency (lower variance = higher confidence)
            if len(sentiment_scores) > 1:
                variance = np.var(list(sentiment_scores.values()))
                consistency_confidence = max(0, 40 - variance * 100)
            else:
                consistency_confidence = 20

            # Confidence from volatility (lower volatility = higher confidence)
            volatility_confidence = max(0, 30 - sentiment_volatility * 50)

            total_confidence = source_confidence + consistency_confidence + volatility_confidence
            return min(total_confidence, 100.0)

        except Exception as e:
            logger.warning(f"Error calculating confidence: {str(e)}")
            return 50.0  # Default confidence

    async def analyze_market_sentiment(self, market_title: str, market_subtitle: str = "",
                                     market_category: str = None) -> Dict:
        """
        Analyze sentiment for a specific market

        Args:
            market_title: Title of the market
            market_subtitle: Subtitle or description of the market
            market_category: Category of the market

        Returns:
            Dictionary containing sentiment analysis results
        """
        try:
            start_time = datetime.utcnow()

            # Extract keywords from market information
            keywords = self._extract_keywords_from_market(market_title, market_subtitle)

            if not keywords:
                return {
                    'sentiment_score': 0.0,
                    'confidence': 10.0,
                    'trend_score': 0.0,
                    'source_scores': {},
                    'details': {
                        'error': 'No keywords extracted from market information',
                        'keywords': keywords
                    }
                }

            logger.info(f"Analyzing sentiment for market: {market_title[:50]}...")

            # Get sentiment from different sources
            tasks = []
            if self.twitter_client:
                tasks.append(self._get_twitter_sentiment(keywords))
            if self.reddit_client:
                tasks.append(self._get_reddit_sentiment(keywords))
            if self.news_api_key:
                tasks.append(self._get_news_sentiment(keywords))

            # Execute sentiment analysis tasks
            sentiment_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            source_scores = {}
            source_names = ['twitter', 'reddit', 'news']

            for i, result in enumerate(sentiment_results):
                if i < len(source_names) and not isinstance(result, Exception):
                    source_scores[source_names[i]] = result

            # Calculate weighted sentiment score
            weighted_sentiment = 0.0
            total_weight = 0.0

            for source, score in source_scores.items():
                if source in self.source_weights:
                    weighted_sentiment += score * self.source_weights[source]
                    total_weight += self.source_weights[source]

            if total_weight > 0:
                final_sentiment = weighted_sentiment / total_weight
            else:
                final_sentiment = 0.0

            # Normalize to -100 to 100 scale
            final_sentiment = final_sentiment * 100

            # Calculate trend score (simplified - would use historical data in production)
            trend_score = self._calculate_trend_score([final_sentiment])

            # Calculate confidence
            volatility = np.std(list(source_scores.values())) if source_scores else 0.5
            confidence = self._calculate_confidence(source_scores, volatility)

            # Determine sentiment classification
            if final_sentiment > 10:
                sentiment_classification = "bullish"
            elif final_sentiment < -10:
                sentiment_classification = "bearish"
            else:
                sentiment_classification = "neutral"

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            result = {
                'sentiment_score': final_sentiment,
                'confidence': confidence,
                'trend_score': trend_score,
                'sentiment_classification': sentiment_classification,
                'source_scores': source_scores,
                'details': {
                    'keywords': keywords,
                    'market_category': market_category,
                    'processing_time_seconds': processing_time,
                    'sources_analyzed': list(source_scores.keys()),
                    'volatility': volatility,
                    'total_weight': total_weight
                }
            }

            logger.info(f"Sentiment analysis completed: {final_sentiment:.2f} ({sentiment_classification}) with {confidence:.1f}% confidence")
            return result

        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return {
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'trend_score': 0.0,
                'sentiment_classification': 'error',
                'source_scores': {},
                'details': {
                    'error': str(e),
                    'processing_failed': True
                }
            }

# Global sentiment analyzer instance
sentiment_analyzer = SentimentAnalyzer()