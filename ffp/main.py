import asyncio
import signal
import sys

from ffp.client.telegram_client import TelegramMonitor
from ffp.client.twitter_client import TwitterClient
from ffp.config.config import config
from ffp.database.database_factory import get_database
from ffp.services.message_processor import MessageProcessor
from ffp.utils import setup_logging

# Set up logging
logger = setup_logging(config.app.log_level)


class TelegramToTwitterBridge:
    def __init__(self):
        self.telegram = TelegramMonitor()
        self.twitter = TwitterClient()
        self.processor = MessageProcessor()
        self.database = get_database()
        self.running = False

    async def start(self):
        """Start the bridge."""
        logger.info('Starting Telegram to Twitter bridge...')

        # Connect to database
        await self.database.connect()

        # Start Telegram client
        asyncio.create_task(self.telegram.run())

        # Start message processing loop
        self.running = True
        asyncio.create_task(self.process_messages())

        # Schedule cleanup
        asyncio.create_task(self.periodic_cleanup())

        logger.info('Bridge started successfully!')

    async def process_messages(self):
        """Process messages from Telegram queue."""
        while self.running:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(
                    self.telegram.message_queue.get(),
                    timeout=config.app.post_interval_seconds,
                )

                # Check if already posted
                if await self.database.is_message_posted(message['id']):
                    logger.info(f'Message {message["id"]} already posted, skipping')
                    continue

                # Process message
                processed = self.processor.process_message(message)

                if not processed['should_post']:
                    logger.info(f'Message {message["id"]} filtered out')
                    continue

                # Post to Twitter
                tweet_id = await self.post_to_twitter(processed)

                if tweet_id:
                    # Save to database
                    await self.database.save_posted_message(
                        telegram_message_id=message['id'],
                        twitter_tweet_id=tweet_id,
                        telegram_channel=self.telegram.channel_username,
                        message_text=processed['text'],
                        media_type=None,  # No media in text-only mode
                    )
                else:
                    # Log error
                    await self.database.log_error(
                        telegram_message_id=message['id'],
                        error_message='Failed to post to Twitter',
                        error_type='twitter_api',
                    )

            except TimeoutError:
                # No messages in queue, continue
                continue
            except Exception as e:
                logger.error(f'Error processing messages: {e}')
                await asyncio.sleep(config.app.retry_delay_seconds)

    async def post_to_twitter(self, message: dict) -> str:
        """Post message to Twitter - text only."""
        try:
            # Always post text only
            tweet_id = await self.twitter.post_text(message['text'])
            return tweet_id

        except Exception as e:
            logger.error(f'Error posting to Twitter: {e}')
            return None

    async def periodic_cleanup(self):
        """Periodic cleanup tasks."""
        while self.running:
            try:
                # Clean up old database records
                await self.database.cleanup_old_records(days=config.app.cleanup_old_records_days)

                # Log statistics
                posts = await self.database.get_recent_posts(limit=config.app.recent_posts_limit)
                errors = await self.database.get_error_count(hours=config.app.error_count_hours)

                logger.info(f'Stats - Recent posts: {len(posts)}, Errors ({config.app.error_count_hours}h): {errors}')

                # Wait configured cleanup interval
                await asyncio.sleep(config.app.cleanup_interval_hours * 3600)

            except Exception as e:
                logger.error(f'Error in periodic cleanup: {e}')
                await asyncio.sleep(3600)

    async def stop(self):
        """Stop the bridge."""
        logger.info('Stopping bridge...')
        self.running = False

        # Stop Telegram client
        await self.telegram.stop()

        # Close database
        await self.database.close()

        logger.info('Bridge stopped')


async def main():
    """Main function."""
    bridge = TelegramToTwitterBridge()
    shutdown_event = asyncio.Event()

    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info('Received interrupt signal')
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start bridge
        await bridge.start()

        # Keep running until shutdown signal
        await shutdown_event.wait()

        # Graceful shutdown
        logger.info('Initiating graceful shutdown...')
        await bridge.stop()

    except Exception as e:
        logger.error(f'Fatal error: {e}')
        await bridge.stop()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
