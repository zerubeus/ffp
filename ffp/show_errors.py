import asyncio
import sys

from ffp.config.config import config
from ffp.database.database_factory import get_database


async def show_errors(hours: int = None, limit: int = None):
    """Display recent errors from the database."""
    # Use config defaults if not provided
    if hours is None:
        hours = config.app.error_display_hours
    if limit is None:
        limit = config.app.error_display_limit

    db = get_database()

    try:
        await db.connect()

        # Get error count
        error_count = await db.get_error_count(hours=hours)
        print(f'\n📊 Error Statistics (last {hours} hours)')
        print(f'{"=" * config.app.separator_line_length}')
        print(f'Total errors: {error_count}')

        if error_count > 0:
            # Get detailed errors using the database interface
            errors = await db.get_recent_errors(hours=hours, limit=limit)

            if errors:
                print(f'\n📋 Recent Errors (showing up to {limit}):')
                print(f'{"=" * config.app.separator_line_length}')

                for error in errors:
                    print(f'\n🔴 Error at {error["occurred_at"]}')
                    print(f'   Message ID: {error["telegram_message_id"]}')
                    print(f'   Type: {error["error_type"]}')
                    print(f'   Error: {error["error_message"]}')
            else:
                print('\nNo error details available.')
        else:
            print('\n✅ No errors found!')

        print(f'\n{"=" * config.app.separator_line_length}')

    except Exception as e:
        print(f'❌ Error accessing database: {e}')
        sys.exit(1)
    finally:
        await db.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Display database errors')
    parser.add_argument(
        '--hours',
        type=int,
        default=config.app.error_display_hours,
        help=f'Number of hours to look back (default: {config.app.error_display_hours})',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=config.app.error_display_limit,
        help=f'Maximum number of errors to display (default: {config.app.error_display_limit})',
    )

    args = parser.parse_args()

    asyncio.run(show_errors(hours=args.hours, limit=args.limit))
