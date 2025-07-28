import logging
from typing import Dict, List, Optional

import aiosqlite

from ffp.config import config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.db_path = config.app.database_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to the database and create tables if needed."""
        self.conn = await aiosqlite.connect(self.db_path)
        await self._create_tables()
        logger.info(f"Connected to database: {self.db_path}")

    async def _create_tables(self):
        """Create necessary tables."""
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS posted_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_message_id INTEGER UNIQUE NOT NULL,
                twitter_tweet_id TEXT,
                telegram_channel TEXT NOT NULL,
                message_text TEXT,
                media_type TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'posted'
            )
        """)

        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_message_id INTEGER,
                error_message TEXT,
                error_type TEXT,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await self.conn.commit()

    async def is_message_posted(self, telegram_message_id: int) -> bool:
        """Check if a message has already been posted."""
        cursor = await self.conn.execute(
            "SELECT id FROM posted_messages WHERE telegram_message_id = ?", (telegram_message_id,)
        )
        result = await cursor.fetchone()
        return result is not None

    async def save_posted_message(
        self,
        telegram_message_id: int,
        twitter_tweet_id: str,
        telegram_channel: str,
        message_text: str = None,
        media_type: str = None,
    ):
        """Save a successfully posted message."""
        await self.conn.execute(
            """
            INSERT INTO posted_messages 
            (telegram_message_id, twitter_tweet_id, telegram_channel, 
             message_text, media_type)
            VALUES (?, ?, ?, ?, ?)
        """,
            (telegram_message_id, twitter_tweet_id, telegram_channel, message_text, media_type),
        )
        await self.conn.commit()
        logger.info(f"Saved posted message: {telegram_message_id} -> {twitter_tweet_id}")

    async def log_error(self, telegram_message_id: int, error_message: str, error_type: str = "general"):
        """Log an error."""
        await self.conn.execute(
            """
            INSERT INTO error_log 
            (telegram_message_id, error_message, error_type)
            VALUES (?, ?, ?)
        """,
            (telegram_message_id, error_message, error_type),
        )
        await self.conn.commit()

    async def get_recent_posts(self, limit: int = 50) -> List[Dict]:
        """Get recent posted messages."""
        cursor = await self.conn.execute(
            """
            SELECT telegram_message_id, twitter_tweet_id, message_text, 
                   media_type, posted_at
            FROM posted_messages
            ORDER BY posted_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        columns = [description[0] for description in cursor.description]
        posts = []
        async for row in cursor:
            posts.append(dict(zip(columns, row)))

        return posts

    async def get_error_count(self, hours: int = 24) -> int:
        """Get error count in the last N hours."""
        cursor = await self.conn.execute(f"""
            SELECT COUNT(*) FROM error_log
            WHERE occurred_at > datetime('now', '-{hours} hours')
        """)

        result = await cursor.fetchone()
        return result[0] if result else 0

    async def cleanup_old_records(self, days: int = 30):
        """Clean up old records."""
        await self.conn.execute(f"""
            DELETE FROM posted_messages
            WHERE posted_at < datetime('now', '-{days} days')
        """)

        await self.conn.execute(f"""
            DELETE FROM error_log
            WHERE occurred_at < datetime('now', '-{days} days')
        """)

        await self.conn.commit()
        logger.info(f"Cleaned up records older than {days} days")

    async def close(self):
        """Close database connection."""
        if self.conn:
            await self.conn.close()
            logger.info("Database connection closed")
