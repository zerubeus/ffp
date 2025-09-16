# Coding for Freedom - FFP

A multi-purpose application suite for freedom of information and fact-checking initiatives. Currently includes a Telegram to X (Twitter) bridge bot, with plans to expand with AI-powered fact-checking agents and other tools.

## Components

### 1. Telegram to X Bridge Bot
Automatically forwards posts from Telegram channels to Twitter/X with smart filtering and content processing.

**[📖 View detailed documentation](docs/x_telegram_bot.md)**

### 2. Fact-Check Agent (Planned)
AI-powered agent using LLMs to verify and fact-check information from various sources.

**[📖 View documentation](docs/fact_check_agent.md)**

## Quick Start

### Prerequisites
- Python 3.13+
- Docker and Docker Compose (for containerized deployment)

### Installation

#### Using Docker Compose (Recommended)

```bash
git clone https://github.com/yourusername/ffp.git
cd ffp
cp .env.example .env
# Edit .env with your credentials
docker-compose up -d
```

#### Local Development

```bash
git clone https://github.com/yourusername/ffp.git
cd ffp
make setup
cp .env.example .env
# Edit .env with your credentials
make run
```

## Development

```bash
# Install dependencies
uv sync

# Run linting and formatting
make lint
make format

# Run tests
make test

# Type checking
make typecheck
```

For detailed component-specific instructions, see the documentation for each component in the `docs/` directory.

## Project Structure

```
ffp/
├── docs/                     # Component documentation
│   ├── x_telegram_bot.md    # Telegram-X bridge documentation
│   └── fact_check_agent.md  # Fact-check agent documentation
├── ffp/                     # Main application code
│   ├── config.py            # Configuration management
│   ├── telegram_client.py   # Telegram API integration
│   ├── twitter_client.py    # X/Twitter API integration
│   ├── message_processor.py # Content processing
│   ├── database_sqlite.py   # SQLite database operations
│   └── utils.py             # Utility functions
├── main.py                  # Main application entry point
├── docker-compose.yml       # Docker services configuration
├── pyproject.toml           # Project configuration and dependencies
├── Makefile                 # Development commands
└── .env                     # Environment configuration
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please open an issue on GitHub.
