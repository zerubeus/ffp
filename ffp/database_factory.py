import os
import logging
from typing import Union

logger = logging.getLogger(__name__)


def get_database() -> Union['PostgresDatabase', 'SQLiteDatabase']:
    """
    Factory function to get the appropriate database instance.
    Uses PostgreSQL if DATABASE_URL is set, otherwise falls back to SQLite.
    """
    database_url = os.getenv('DATABASE_URL', '')
    
    if database_url and 'postgresql' in database_url:
        from ffp.database_postgres import PostgresDatabase
        logger.info('Using PostgreSQL database')
        return PostgresDatabase()
    else:
        from ffp.database_sqlite import SQLiteDatabase
        logger.info('Using SQLite database (local mode)')
        return SQLiteDatabase()