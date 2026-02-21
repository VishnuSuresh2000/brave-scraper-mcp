# Stealth Browser MCP Server - Optimized Production Dockerfile
# Uses official uv Python image for fast package management

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Labels
LABEL maintainer="Ruto AI Assistant"
LABEL description="Stealth web scraping MCP server with Brave Search support"
LABEL version="1.0.0"

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV STEALTH_MODE=true
ENV CAPTCHA_AUTO_SOLVE=true
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# Install system dependencies for Xvfb + GUI + OCR + Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Xvfb and X11
    xvfb \
    x11-utils \
    xdotool \
    scrot \
    # Python GUI
    python3-tk \
    python3-dev \
    libx11-dev \
    libxtst-dev \
    libxext-dev \
    # OCR dependencies
    tesseract-ocr \
    libtesseract-dev \
    # Additional dependencies for Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    # Fonts
    fonts-liberation \
    fonts-noto-color-emoji \
    # Utilities
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -s /bin/bash scraper && \
    mkdir -p /home/scraper/app /home/scraper/browser_data && \
    chown -R scraper:scraper /home/scraper

WORKDIR /home/scraper/app

# Copy dependency files first for better caching
COPY pyproject.toml .
COPY requirements.txt .

# Install Python dependencies using uv (fast!)
RUN uv pip install --system -r requirements.txt

# Install Patchright Chrome
RUN patchright install chrome

# Copy application code
COPY src/ ./src/
COPY templates/ ./templates/

# Set permissions
RUN chown -R scraper:scraper /home/scraper

# Switch to non-root user
USER scraper

# Expose MCP server port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Entry point
COPY entrypoint.sh .
ENTRYPOINT ["./entrypoint.sh"]
