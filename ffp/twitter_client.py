import logging
import os
from typing import Dict, List, Optional

import tweepy

from ffp.config import config

logger = logging.getLogger(__name__)


class TwitterClient:
    def __init__(self):
        self.api = self._initialize_api()
        self.client = self._initialize_client()

    def _initialize_api(self) -> tweepy.API:
        """Initialize Tweepy API v1.1 for media uploads."""
        auth = tweepy.OAuthHandler(config.twitter.api_key, config.twitter.api_secret)
        auth.set_access_token(config.twitter.access_token, config.twitter.access_token_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True)

        # Verify credentials
        try:
            api.verify_credentials()
            logger.info("Twitter API v1.1 authentication successful")
        except Exception as e:
            logger.error(f"Twitter API v1.1 authentication failed: {e}")
            raise

        return api

    def _initialize_client(self) -> tweepy.Client:
        """Initialize Tweepy Client for API v2."""
        client = tweepy.Client(
            bearer_token=config.twitter.bearer_token,
            consumer_key=config.twitter.api_key,
            consumer_secret=config.twitter.api_secret,
            access_token=config.twitter.access_token,
            access_token_secret=config.twitter.access_token_secret,
            wait_on_rate_limit=True,
        )

        logger.info("Twitter API v2 client initialized")
        return client

    def post_text(self, text: str) -> Optional[str]:
        """Post a text-only tweet."""
        try:
            # Truncate text if too long (280 characters for Twitter)
            if len(text) > 280:
                text = text[:277] + "..."

            response = self.client.create_tweet(text=text)
            tweet_id = response.data["id"]
            logger.info(f"Posted tweet: {tweet_id}")
            return tweet_id

        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return None

    def post_with_media(self, text: str, media_path: str, media_type: str) -> Optional[str]:
        """Post a tweet with media (photo or video)."""
        try:
            # Upload media using API v1.1
            if media_type == "photo":
                media_ids = self._upload_photo(media_path)
            elif media_type == "video":
                media_ids = self._upload_video(media_path)
            else:
                logger.warning(f"Unsupported media type: {media_type}")
                return self.post_text(text)

            if not media_ids:
                logger.warning("Media upload failed, posting text only")
                return self.post_text(text)

            # Truncate text if too long
            if len(text) > 280:
                text = text[:277] + "..."

            # Post tweet with media using API v2
            response = self.client.create_tweet(text=text, media_ids=media_ids)
            tweet_id = response.data["id"]
            logger.info(f"Posted tweet with media: {tweet_id}")

            # Clean up media file
            try:
                os.remove(media_path)
            except Exception as e:
                logger.warning(f"Failed to delete media file: {e}")

            return tweet_id

        except Exception as e:
            logger.error(f"Error posting tweet with media: {e}")
            return None

    def _upload_photo(self, photo_path: str) -> Optional[List[str]]:
        """Upload photo and return media ID."""
        try:
            media = self.api.media_upload(photo_path)
            return [str(media.media_id)]
        except Exception as e:
            logger.error(f"Error uploading photo: {e}")
            return None

    def _upload_video(self, video_path: str) -> Optional[List[str]]:
        """Upload video and return media ID."""
        try:
            # Check video size (512MB limit for Twitter)
            file_size = os.path.getsize(video_path)
            if file_size > 512 * 1024 * 1024:
                logger.error("Video file too large (>512MB)")
                return None

            media = self.api.media_upload(video_path, media_category="tweet_video")
            return [str(media.media_id)]
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            return None

    def check_rate_limits(self) -> Dict[str, int]:
        """Check current rate limits."""
        try:
            limits = self.api.rate_limit_status()
            tweet_limit = limits["resources"]["statuses"]["/statuses/update"]
            return {"remaining": tweet_limit["remaining"], "limit": tweet_limit["limit"], "reset": tweet_limit["reset"]}
        except Exception as e:
            logger.error(f"Error checking rate limits: {e}")
            return {"remaining": -1, "limit": -1, "reset": -1}
