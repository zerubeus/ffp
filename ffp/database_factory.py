from ffp.database_sqlite import SQLiteDatabase


def get_database() -> SQLiteDatabase:
    """
    Factory function to get the SQLite database instance.
    """
    return SQLiteDatabase()