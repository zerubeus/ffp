import logging
import os
from typing import Dict, List, Optional

import asyncpg

from ffp.config import config

logger = logging.getLogger(__name__)


class PostgresDatabase:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', '')
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Connect to the database and create tables if needed."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                timeout=60,
                command_timeout=60
            )
            await self._create_tables()
            logger.info(f"Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def _create_tables(self):
        """Create necessary tables (already handled by init.sql, but kept for compatibility)."""
        async with self.pool.acquire() as conn:
            # Tables are created by init.sql, but we can verify they exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS posted_messages (
                    id SERIAL PRIMARY KEY,
                    telegram_message_id BIGINT UNIQUE NOT NULL,
                    twitter_tweet_id VARCHAR(255),
                    telegram_channel VARCHAR(255) NOT NULL,
                    message_text TEXT,
                    media_type VARCHAR(50),
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'posted'
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS error_log (
                    id SERIAL PRIMARY KEY,
                    telegram_message_id BIGINT,
                    error_message TEXT,
                    error_type VARCHAR(100),
                    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    async def is_message_posted(self, telegram_message_id: int) -> bool:
        """Check if a message has already been posted."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM posted_messages WHERE telegram_message_id = $1)",
                telegram_message_id
            )
            return result

    async def save_posted_message(
        self,
        telegram_message_id: int,
        twitter_tweet_id: str,
        telegram_channel: str,
        message_text: str = None,
        media_type: str = None,
    ):
        """Save a successfully posted message."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO posted_messages 
                (telegram_message_id, twitter_tweet_id, telegram_channel, 
                 message_text, media_type)
                VALUES ($1, $2, $3, $4, $5)
                """,
                telegram_message_id, twitter_tweet_id, telegram_channel, 
                message_text, media_type
            )
            logger.info(f"Saved posted message: {telegram_message_id} -> {twitter_tweet_id}")

    async def log_error(self, telegram_message_id: int, error_message: str, error_type: str = "general"):
        """Log an error."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO error_log 
                (telegram_message_id, error_message, error_type)
                VALUES ($1, $2, $3)
                """,
                telegram_message_id, error_message, error_type
            )

    async def get_recent_posts(self, limit: int = 50) -> List[Dict]:
        """Get recent posted messages."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT telegram_message_id, twitter_tweet_id, message_text, 
                       media_type, posted_at
                FROM posted_messages
                ORDER BY posted_at DESC
                LIMIT $1
                """,
                limit
            )
            
            return [dict(row) for row in rows]

    async def get_error_count(self, hours: int = 24) -> int:
        """Get error count in the last N hours."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT COUNT(*) FROM error_log
                WHERE occurred_at > NOW() - INTERVAL '$1 hours'
                """,
                hours
            )
            return result or 0

    async def cleanup_old_records(self, days: int = 30):
        """Clean up old records."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM posted_messages
                WHERE posted_at < NOW() - INTERVAL '$1 days'
                """,
                days
            )

            await conn.execute(
                """
                DELETE FROM error_log
                WHERE occurred_at < NOW() - INTERVAL '$1 days'
                """,
                days
            )

            logger.info(f"Cleaned up records older than {days} days")

    async def close(self):
        """Close database connection."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")