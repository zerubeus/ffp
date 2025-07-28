FROM python:3.13-slim

# Install UV package manager
ENV UV_VERSION=0.5.11
RUN pip install --no-cache-dir uv==$UV_VERSION

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create downloads and logs directories
RUN mkdir -p /app/downloads /app/logs

# Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run the application
CMD ["uv", "run", "python", "main.py"]