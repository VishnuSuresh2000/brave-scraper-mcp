# Brave Scraper MCP Server - Optimized Production Dockerfile
# Uses official Playwright image (minimal for Patchright compatibility)

FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

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

# Install Xvfb + OCR dependencies (not included in Playwright image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    xdotool \
    scrot \
    tesseract-ocr \
    libtesseract-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -s /bin/bash scraper && \
    mkdir -p /home/scraper/app /home/scraper/browser_data && \
    chown -R scraper:scraper /home/scraper

WORKDIR /home/scraper/app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Patchright Chrome (uses Playwright's pre-installed browser base)
RUN patchright install chrome

# Copy application code
COPY src/ ./src/
COPY templates/ ./templates/
COPY pyproject.toml .

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
