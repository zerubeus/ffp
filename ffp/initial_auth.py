import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()


async def authenticate():
    """Perform initial authentication to create session file."""
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE')
    session_name = os.getenv('TELEGRAM_SESSION_NAME', 'telegram_session')

    if not all([api_id, api_hash, phone]):
        print('Error: Missing required environment variables')
        print('Please ensure TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_PHONE are set')
        return

    print(f'Creating session file: {session_name}.session')
    print('You will be asked for the verification code sent to your Telegram app.')
    print('This only needs to be done once.\n')

    client = TelegramClient(session_name, int(api_id), api_hash)

    await client.start(phone=phone)

    print('\n✅ Authentication successful!')
    print(f'Session file created: {session_name}.session')
    print('\nIMPORTANT: Copy this session file to your Docker volume or VPC:')
    print(f'  - Local: cp {session_name}.session ./sessions/')
    print("  - Docker: The session will persist in the 'telegram_sessions' volume")
    print(f'  - VPC: Upload {session_name}.session to /app/sessions/ in your container')

    # Test the connection
    me = await client.get_me()
    print(f'\nLogged in as: {me.first_name} {me.last_name or ""}')

    await client.disconnect()


if __name__ == '__main__':
    asyncio.run(authenticate())
