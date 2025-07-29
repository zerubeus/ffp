import asyncio
import logging
from pathlib import Path
from typing import Any

from telethon import TelegramClient, events
from telethon.tl.types import Message, MessageMediaDocument, MessageMediaPhoto

from ffp.config import config

logger = logging.getLogger(__name__)


class TelegramMonitor:
    def __init__(self):
        self.client = TelegramClient(config.telegram.session_name, config.telegram.api_id, config.telegram.api_hash)
        self.channel_username = config.telegram.channel_username
        self.media_path = Path(config.app.media_download_path)
        self.media_path.mkdir(exist_ok=True)
        self.message_queue: asyncio.Queue = asyncio.Queue()

    async def start(self):
        """Start the Telegram client and connect."""
        await self.client.start(phone=config.telegram.phone)

        # Register event handler
        @self.client.on(events.NewMessage(chats=self.channel_username))
        async def handle_new_message(event):
            await self._process_message(event.message)

    async def _process_message(self, message: Message):
        """Process incoming Telegram message."""
        try:
            message_data = {
                'id': message.id,
                'text': message.text or '',
                'date': message.date,
                'media': None,
                'media_type': None,
            }

            # Handle media
            if message.media:
                media_info = await self._download_media(message)
                if media_info:
                    message_data['media'] = media_info['path']
                    message_data['media_type'] = media_info['type']

            await self.message_queue.put(message_data)

        except Exception as e:
            logger.error(f'Error processing message {message.id}: {e}')

    async def _download_media(self, message: Message) -> dict[str, str] | None:
        """Download media from message."""
        try:
            if isinstance(message.media, MessageMediaPhoto):
                file_path = await message.download_media(self.media_path)
                return {'path': str(file_path), 'type': 'photo'}

            elif isinstance(message.media, MessageMediaDocument):
                mime_type = message.media.document.mime_type
                if mime_type and (mime_type.startswith('image/') or mime_type.startswith('video/')):
                    file_path = await message.download_media(self.media_path)
                    media_type = 'video' if mime_type.startswith('video/') else 'photo'
                    return {'path': str(file_path), 'type': media_type}

            return None

        except Exception as e:
            logger.error(f'Error downloading media: {e}')
            return None

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
