from ffp.database_postgres import PostgresDatabase


def get_database() -> PostgresDatabase:
    """
    Factory function to get the PostgreSQL database instance.
    """
    return PostgresDatabase()