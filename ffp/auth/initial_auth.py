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

    # Type narrowing - we know these are not None after the check above
    assert api_id is not None
    assert api_hash is not None
    assert phone is not None

    client = TelegramClient(session_name, int(api_id), api_hash)

    await client.start(phone=phone)  # type: ignore[misc]

    print('\n✅ Authentication successful!')
    print(f'Session file created: {session_name}.session')
    print('\nIMPORTANT: Copy this session file to your Docker volume or VPC:')
    print(f'  - Local: cp {session_name}.session ./sessions/')
    print("  - Docker: The session will persist in the 'telegram_sessions' volume")
    print(f'  - VPC: Upload {session_name}.session to /app/sessions/ in your container')

    # Test the connection
    me = await client.get_me()
    first_name = getattr(me, 'first_name', 'Unknown')
    last_name = getattr(me, 'last_name', '')
    print(f'\nLogged in as: {first_name} {last_name or ""}')

    await client.disconnect()  # type: ignore[misc]


if __name__ == '__main__':
    asyncio.run(authenticate())
