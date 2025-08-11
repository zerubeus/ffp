import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=False)


@dataclass
class TelegramConfig:
    api_id: int
    api_hash: str
    phone: str
    session_name: str
    channel_username: str


@dataclass
class TwitterConfig:
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str
    bearer_token: str


@dataclass
class AppConfig:
    post_interval_seconds: int
    max_retries: int
    log_level: str
    media_download_path: str


class Config:
    def __init__(self):
        self.telegram = self._load_telegram_config()
        self.twitter = self._load_twitter_config()
        self.app = self._load_app_config()

        os.makedirs(self.app.media_download_path, exist_ok=True)

    @staticmethod
    def _load_telegram_config() -> TelegramConfig:
        api_id = os.getenv('TELEGRAM_API_ID')
        if not api_id:
            raise ValueError('TELEGRAM_API_ID is required')

        return TelegramConfig(
            api_id=int(api_id),
            api_hash=os.getenv('TELEGRAM_API_HASH', ''),
            phone=os.getenv('TELEGRAM_PHONE', ''),
            session_name=os.getenv('TELEGRAM_SESSION_NAME', 'telegram_session'),
            channel_username=os.getenv('TELEGRAM_CHANNEL_USERNAME', ''),
        )

    @staticmethod
    def _load_twitter_config() -> TwitterConfig:
        return TwitterConfig(
            api_key=os.getenv('X_API_KEY', ''),
            api_secret=os.getenv('X_API_SECRET', ''),
            access_token=os.getenv('X_ACCESS_TOKEN', ''),
            access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET', ''),
            bearer_token=os.getenv('X_BEARER_TOKEN', ''),
        )

    @staticmethod
    def _load_app_config() -> AppConfig:
        return AppConfig(
            post_interval_seconds=int(os.getenv('POST_INTERVAL_SECONDS', '60')),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            media_download_path=os.getenv('MEDIA_DOWNLOAD_PATH', './downloads'),
        )


config = Config()
