import asyncio
import sys
from datetime import datetime, timedelta

from ffp.database_factory import get_database


async def show_errors(hours: int = 24, limit: int = 50):
    """Display recent errors from the database."""
    db = get_database()

    try:
        await db.connect()

        # Get error count
        error_count = await db.get_error_count(hours=hours)
        print(f'\n📊 Error Statistics (last {hours} hours)')
        print(f'{"=" * 50}')
        print(f'Total errors: {error_count}')

        if error_count > 0:
            # Get detailed errors if using SQLite (direct query)
            if hasattr(db, 'db'):  # SQLite implementation
                cutoff_time = datetime.now() - timedelta(hours=hours)
                cursor = await db.db.execute(
                    """
                    SELECT telegram_message_id, error_message, error_type, occurred_at
                    FROM error_log
                    WHERE occurred_at > ?
                    ORDER BY occurred_at DESC
                    LIMIT ?
                    """,
                    (cutoff_time.isoformat(), limit),
                )

                errors = await cursor.fetchall()

                if errors:
                    print(f'\n📋 Recent Errors (showing up to {limit}):')
                    print(f'{"=" * 50}')

                    for error in errors:
                        msg_id, err_msg, err_type, occurred_at = error
                        print(f'\n🔴 Error at {occurred_at}')
                        print(f'   Message ID: {msg_id}')
                        print(f'   Type: {err_type}')
                        print(f'   Error: {err_msg}')
                else:
                    print('\nNo error details available.')
        else:
            print('\n✅ No errors found!')

        print(f'\n{"=" * 50}')

    except Exception as e:
        print(f'❌ Error accessing database: {e}')
        sys.exit(1)
    finally:
        await db.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Display database errors')
    parser.add_argument('--hours', type=int, default=24, help='Number of hours to look back (default: 24)')
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of errors to display (default: 50)')

    args = parser.parse_args()

    asyncio.run(show_errors(hours=args.hours, limit=args.limit))
