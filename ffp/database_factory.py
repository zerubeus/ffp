import os
from typing import Union

from ffp.database import Database
from ffp.database_postgres import PostgresDatabase


def get_database() -> Union[Database, PostgresDatabase]:
    """
    Factory function to get the appropriate database instance.
    Returns PostgreSQL if DATABASE_URL is set, otherwise SQLite.
    """
    if os.getenv('DATABASE_URL'):
        return PostgresDatabase()
    else:
        return Database()