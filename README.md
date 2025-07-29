# Coding for Freedom - FFP

A Telegram to X (Twitter) bridge application that automatically forwards posts from Telegram channels to Twitter/X.

## Features

- **Automatic Message Forwarding**: Monitors Telegram channels and posts to X
- **Media Support**: Handles photos and videos
- **Smart Text Processing**: Adds hashtags (#FreePalestine #Palestine)
- **Duplicate Prevention**: PostgreSQL database tracking to avoid reposting
- **Error Handling**: Robust error logging and retry mechanisms
- **Content Filtering**: Filters out spam and irrelevant content
- **Production Ready**: PostgreSQL database with connection pooling
- **Docker Support**: Easy deployment with docker-compose

## Prerequisites

- Python 3.13+
- PostgreSQL 13+ (or use Docker Compose for automatic setup)
- Telegram API credentials (api_id and api_hash)
- X/Twitter API credentials (API keys and tokens)

## Installation

### Option 1: Using Docker Compose (Recommended)

1. Clone the repository:

```bash
git clone https://github.com/yourusername/ffp.git
cd ffp
```

2. Copy the environment file:

```bash
cp .env.example .env
```

3. Edit `.env` with your credentials:

   - Get Telegram API credentials from https://my.telegram.org
   - Get X API credentials from https://developer.twitter.com

4. Start the application with PostgreSQL:

```bash
docker-compose up -d
```

### Option 2: Local Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/ffp.git
cd ffp
```

2. Install PostgreSQL (if not using Docker):

```bash
docker compose up -d postgresql
```

3. Run the setup (installs UV if needed and sets up the project):

```bash
make setup
```

4. Activate the virtual environment:

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

5. Set up configuration:

```bash
cp .env.example .env
```

6. Edit `.env` with your credentials and database URL:
   - Get Telegram API credentials from https://my.telegram.org
   - Get X API credentials from https://developer.twitter.com
   - Set DATABASE_URL to your PostgreSQL connection string

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

# PostgreSQL Configuration
DATABASE_URL=postgresql://ffp:ffp_secret@localhost:5432/ffp_db
POSTGRES_USER=ffp
POSTGRES_PASSWORD=ffp_secret
POSTGRES_DB=ffp_db

# Application Settings
POST_INTERVAL_SECONDS=60
LOG_LEVEL=INFO
```

## Usage

### Quick Start with Docker

```bash
# Start all services (PostgreSQL + App)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

### Local Development

```bash
# Install dependencies
uv sync

# Initialize database (if running PostgreSQL locally)
psql -U ffp -d ffp_db -f scripts/init.sql

# Run the application
uv run python main.py

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
├── ffp/
│   ├── config.py             # Configuration management
│   ├── telegram_client.py    # Telegram API integration
│   ├── twitter_client.py     # X/Twitter API integration
│   ├── message_processor.py  # Content processing
│   ├── database_postgres.py  # PostgreSQL database operations
│   ├── database_factory.py   # Database factory pattern
│   └── utils.py              # Utility functions
├── scripts/
│   └── init.sql              # Database initialization script
├── main.py                   # Main application entry point
├── docker-compose.yml        # Docker services configuration
├── pyproject.toml            # Project configuration and dependencies
└── .env                      # Environment configuration
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

- PostgreSQL with connection pooling for high performance
- Tracks posted messages to prevent duplicates
- Indexes for fast lookups
- Logs errors for debugging
- Periodic cleanup of old records
- Statistics view for monitoring posting activity

## Troubleshooting

1. **Database Connection Issues**:

   - Ensure PostgreSQL is running: `docker-compose ps`
   - Check DATABASE_URL in your .env file
   - Verify database credentials match docker-compose.yml

2. **Authentication Issues**:

   - Ensure your API credentials are correct
   - Check that your X app has read/write permissions

3. **Rate Limits**:

   - The app respects X API rate limits automatically
   - Adjust POST_INTERVAL_SECONDS if needed

4. **Media Upload Failures**:
   - Check file size limits (512MB for videos)
   - Ensure sufficient disk space for downloads

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please open an issue on GitHub.
