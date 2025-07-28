# Coding for Freedom - FFP

A Telegram to X (Twitter) bridge application that automatically forwards posts from Telegram channels to Twitter/X.

## Features

- **Automatic Message Forwarding**: Monitors Telegram channels and posts to X
- **Media Support**: Handles photos and videos
- **Smart Text Processing**: Adds hashtags (#FreePalestine #Palestine)
- **Duplicate Prevention**: Database tracking to avoid reposting
- **Error Handling**: Robust error logging and retry mechanisms
- **Content Filtering**: Filters out spam and irrelevant content

## Prerequisites

- Python 3.9+
- Telegram API credentials (api_id and api_hash)
- X/Twitter API credentials (API keys and tokens)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/ffp.git
cd ffp
```

2. Run the setup (installs UV if needed and sets up the project):

```bash
make setup
```

3. Activate the virtual environment:

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

4. Set up configuration:

```bash
cp .env.example .env
```

5. Edit `.env` with your credentials:
   - Get Telegram API credentials from https://my.telegram.org
   - Get X API credentials from https://developer.twitter.com

## Configuration

Edit the `.env` file with your settings:

```env
# Telegram Configuration
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890
TELEGRAM_CHANNEL_USERNAME=@channel_name

# X (Twitter) Configuration
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
X_BEARER_TOKEN=your_bearer_token

# Application Settings
POST_INTERVAL_SECONDS=60
LOG_LEVEL=INFO
```

## Usage

### Quick Start

```bash
uv sync       # Install dependencies
uv run python main.py  # Run the application
# Or using Make:
make install  # Install dependencies  
make run      # Run the application
make dev      # Install with dev dependencies
make lint     # Run linting
make format   # Format code
```

On first run, you'll need to authenticate with Telegram using your phone number.

## Project Structure

```
ffp/
├── src/
│   ├── config.py          # Configuration management
│   ├── telegram_client.py # Telegram API integration
│   ├── twitter_client.py  # X/Twitter API integration
│   ├── message_processor.py # Content processing
│   ├── database.py        # SQLite database operations
│   └── utils.py           # Utility functions
├── main.py                # Main application entry point
├── pyproject.toml         # Project configuration and dependencies
└── .env                   # Environment configuration
```

## Features in Detail

### Message Processing

- Automatically adds #FreePalestine and #Palestine hashtags
- Cleans Telegram formatting for Twitter compatibility
- Handles long messages with truncation
- Filters spam and promotional content

### Media Handling

- Downloads photos and videos from Telegram
- Uploads media to X with appropriate formatting
- Cleans up temporary files after posting

### Database

- Tracks posted messages to prevent duplicates
- Logs errors for debugging
- Periodic cleanup of old records

## Troubleshooting

1. **Authentication Issues**:

   - Ensure your API credentials are correct
   - Check that your X app has read/write permissions

2. **Rate Limits**:

   - The app respects X API rate limits automatically
   - Adjust POST_INTERVAL_SECONDS if needed

3. **Media Upload Failures**:
   - Check file size limits (512MB for videos)
   - Ensure sufficient disk space for downloads

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please open an issue on GitHub.
