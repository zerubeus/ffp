import logging
import os
import aiosqlite
from typing import Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class SQLiteDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use /app/data in Docker, or local directory otherwise
            if os.path.exists('/app/data'):
                db_dir = Path('/app/data')
            else:
                db_dir = Path('.')
            db_dir.mkdir(exist_ok=True)
            self.db_path = str(db_dir / 'ffp.db')
        else:
            self.db_path = db_path
        self.db = None

    async def connect(self):
        """Connect to the database and create tables if needed."""
        try:
            self.db = await aiosqlite.connect(self.db_path)
            await self._create_tables()
            logger.info('Connected to SQLite database')
        except Exception as e:
            logger.error(f'Failed to connect to SQLite: {e}')
            raise

    async def _create_tables(self):
        """Create necessary tables."""
        await self.db.execute("""
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

        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_message_id INTEGER,
                error_message TEXT,
                error_type TEXT,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.db.commit()

    async def is_message_posted(self, telegram_message_id: int) -> bool:
        """Check if a message has already been posted."""
        cursor = await self.db.execute(
            'SELECT 1 FROM posted_messages WHERE telegram_message_id = ?', 
            (telegram_message_id,)
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
        await self.db.execute(
            """
            INSERT INTO posted_messages 
            (telegram_message_id, twitter_tweet_id, telegram_channel, 
             message_text, media_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_message_id, twitter_tweet_id, telegram_channel, 
             message_text, media_type)
        )
        await self.db.commit()
        logger.info(f'Saved posted message: {telegram_message_id} -> {twitter_tweet_id}')

    async def log_error(self, telegram_message_id: int, error_message: str, error_type: str = 'general'):
        """Log an error."""
        await self.db.execute(
            """
            INSERT INTO error_log 
            (telegram_message_id, error_message, error_type)
            VALUES (?, ?, ?)
            """,
            (telegram_message_id, error_message, error_type)
        )
        await self.db.commit()

    async def get_recent_posts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent posted messages."""
        cursor = await self.db.execute(
            """
            SELECT telegram_message_id, twitter_tweet_id, message_text, 
                   media_type, posted_at
            FROM posted_messages
            ORDER BY posted_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        rows = await cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    async def get_error_count(self, hours: int = 24) -> int:
        """Get error count in the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cursor = await self.db.execute(
            """
            SELECT COUNT(*) FROM error_log
            WHERE occurred_at > ?
            """,
            (cutoff_time.isoformat(),)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0

    async def get_recent_errors(self, hours: int = 24, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent errors from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cursor = await self.db.execute(
            """
            SELECT telegram_message_id, error_message, error_type, occurred_at
            FROM error_log
            WHERE occurred_at > ?
            ORDER BY occurred_at DESC
            LIMIT ?
            """,
            (cutoff_time.isoformat(), limit),
        )
        
        rows = await cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    async def cleanup_old_records(self, days: int = 30):
        """Clean up old records."""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        await self.db.execute(
            """
            DELETE FROM posted_messages
            WHERE posted_at < ?
            """,
            (cutoff_time.isoformat(),)
        )

        await self.db.execute(
            """
            DELETE FROM error_log
            WHERE occurred_at < ?
            """,
            (cutoff_time.isoformat(),)
        )
        
        await self.db.commit()
        logger.info(f'Cleaned up records older than {days} days')

    async def close(self):
        """Close database connection."""
        if self.db:
            await self.db.close()
            logger.info('Database connection closed')