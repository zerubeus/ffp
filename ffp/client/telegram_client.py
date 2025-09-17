import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from telethon import TelegramClient, events
from telethon.tl.types import Message

from ffp.config.config import config

logger = logging.getLogger(__name__)


class TelegramMonitor:
    def __init__(self):
        # Ensure session directory exists
        session_path = Path(config.telegram.session_name)
        session_path.parent.mkdir(parents=True, exist_ok=True)

        self.client = TelegramClient(config.telegram.session_name, config.telegram.api_id, config.telegram.api_hash)
        self.channel_username = config.telegram.channel_username
        self.message_queue: asyncio.Queue = asyncio.Queue()

    async def start(self):
        """Start the Telegram client and connect."""
        # Start with session persistence - will only ask for code on first run
        await self.client.start(
            phone=lambda: config.telegram.phone,
            password=lambda: os.getenv('TELEGRAM_2FA_PASSWORD', ''),  # Optional 2FA password
        )

        logger.info('Telegram client started successfully')

        # Register event handler
        @self.client.on(events.NewMessage(chats=self.channel_username))
        async def handle_new_message(event):
            await self._process_message(event.message)

    async def _process_message(self, message: Message):
        """Process incoming Telegram message - text only."""
        try:
            # Only process messages with text content
            if message.text:
                message_data = {
                    'id': message.id,
                    'text': message.text,
                    'date': message.date,
                }

                await self.message_queue.put(message_data)
                logger.info(f'Message {message.id} added to queue')
            else:
                logger.debug(f'Message {message.id} skipped - no text content')

        except Exception as e:
            logger.error(f'Error processing message {message.id}: {e}')

    async def get_recent_messages(self, limit: int = 10) -> list[dict[str, Any]] | None:
        """Get recent messages from channel."""
        messages = []
        async for message in self.client.iter_messages(self.channel_username, limit=limit):
            message_data = {'id': message.id, 'text': message.text or '', 'date': message.date}
            messages.append(message_data)
        return messages

    async def run(self):
        """Run the client and keep it alive."""
        await self.start()
        logger.info(f'Monitoring channel: {self.channel_username}')
        await self.client.run_until_disconnected()

    async def stop(self):
        """Stop the Telegram client."""
        await self.client.disconnect()
        logger.info('Telegram client disconnected')
