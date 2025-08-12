FROM python:3.13-slim

# Install git (required for uv-dynamic-versioning)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install UV package manager
ENV UV_VERSION=0.5.11
RUN pip install --no-cache-dir uv==$UV_VERSION

# Set working directory
WORKDIR /app

# Copy dependency files and git info for versioning
COPY pyproject.toml uv.lock README.md ./
COPY .git .git

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create necessary directories including session storage
RUN mkdir -p /app/downloads /app/logs /app/sessions

# Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variable for session location
ENV TELEGRAM_SESSION_NAME=/app/sessions/telegram_session.session

# Run the application
CMD ["uv", "run", "python", "-m", "ffp.main"]