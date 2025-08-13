import logging

import tweepy

from ffp.config import config

logger = logging.getLogger(__name__)


class TwitterClient:
    def __init__(self):
        self.client = self._initialize_client()

    def _initialize_client(self) -> tweepy.Client:
        """Initialize Tweepy Client for API v2."""
        # Use OAuth1 for user context (required for posting)
        client = tweepy.Client(
            consumer_key=config.twitter.api_key,
            consumer_secret=config.twitter.api_secret,
            access_token=config.twitter.access_token,
            access_token_secret=config.twitter.access_token_secret,
            wait_on_rate_limit=True,
        )

        logger.info('Twitter API v2 client initialized')
        return client

    def post_text(self, text: str) -> str | None:
        """Post a text-only tweet."""
        try:
            # Truncate text if too long (280 characters for Twitter)
            if len(text) > 280:
                text = text[:277] + '...'

            response = self.client.create_tweet(text=text)
            tweet_id = response.data['id']
            logger.info(f'Posted tweet: {tweet_id}')
            return tweet_id

        except Exception as e:
            logger.error(f'Error posting tweet: {e}')
            return None


    def check_rate_limits(self) -> dict[str, int]:
        """Check current rate limits."""
        # Rate limit checking not available without API v1.1
        return {'remaining': -1, 'limit': -1, 'reset': -1}
