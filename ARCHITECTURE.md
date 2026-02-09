# Brave Scraper MCP Server - Architecture

**Task ID:** 35  
**Status Tracker:** http://172.18.0.8:8000  
**Created:** 2026-02-09

---

## Overview

A stealth web scraping MCP server using **Patchright + Xvfb + PyAutoGUI** for Brave Search with CAPTCHA bypass capabilities. Deployed as a Docker container with HTTP transport for mcporter integration.

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **MCP Framework** | Python SDK v2 (mcp[cli]) | Server implementation with decorators |
| **Browser Automation** | Patchright | Undetected Playwright fork |
| **Virtual Display** | Xvfb | Anti-headless detection |
| **CAPTCHA Solver** | PyAutoGUI + OpenCV + Tesseract | Human-like mouse, template matching |
| **Content Extraction** | trafilatura / readability | Smart content cleanup |
| **Transport** | Streamable HTTP | Docker deployment, mcporter compatible |
| **Containerization** | Docker + Alpine | Production deployment |

---

## Project Structure

```
brave-scraper-mcp/
├── src/
│   ├── __init__.py
│   ├── server.py              # MCP server entry point
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── manager.py         # Browser lifecycle (Patchright)
│   │   ├── stealth.py         # Xvfb + anti-detection config
│   │   └── captcha.py         # CAPTCHA solving logic
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── navigation.py      # browser_navigate, browser_back
│   │   ├── interaction.py     # browser_click, browser_fill, browser_hover
│   │   ├── extraction.py      # browser_screenshot, browser_evaluate
│   │   └── brave_search.py    # brave_search, brave_extract
│   └── utils/
│       ├── __init__.py
│       ├── content_cleaner.py # Readability-style extraction
│       └── mouse.py           # Human-like mouse movements
├── templates/
│   ├── turnstile_checkbox.png # CAPTCHA element templates
│   └── verify_button.png
├── tests/
│   ├── test_stealth.py        # Bot detection tests
│   ├── test_captcha.py        # CAPTCHA solving tests
│   └── test_brave_search.py   # Search flow tests
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
└── README.md
```

---

## MCP Tools

### Core Browser Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `browser_navigate` | Navigate to URL | `url: str`, `wait_until: str = "load"` |
| `browser_screenshot` | Capture page/element | `name: str`, `selector: str = None`, `full_page: bool = False` |
| `browser_click` | Click element | `selector: str` |
| `browser_fill` | Fill input field | `selector: str`, `value: str` |
| `browser_hover` | Hover element | `selector: str` |
| `browser_evaluate` | Execute JavaScript | `script: str` |
| `browser_solve_captcha` | Auto-solve CAPTCHA | `timeout: int = 30` |

### Business Logic Tools

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `brave_search` | Search Brave Search | `query: str`, `count: int = 10` | `list[SearchResult]` |
| `brave_extract` | Extract clean content from URL | `url: str`, `max_length: int = 5000` | `ExtractedContent` |

### Data Models

```python
from pydantic import BaseModel

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    position: int

class ExtractedContent(BaseModel):
    title: str
    url: str
    content: str          # Clean, readable text only
    summary: str = None   # Optional TL;DR for long content
    word_count: int
```

---

## Stealth Configuration

### Patchright Setup

```python
# Maximum stealth configuration
context = await playwright.chromium.launch_persistent_context(
    user_data_dir="/data/browser",
    channel="chrome",         # Real Chrome, not Chromium
    headless=False,           # Required for Xvfb + PyAutoGUI
    no_viewport=True,
    args=[
        '--display=:99',
        '--disable-blink-features=AutomationControlled',
    ]
)
```

### Anti-Detection Features

| Feature | Implementation |
|---------|----------------|
| **Runtime.enable leak** | Patchright handles (isolated ExecutionContexts) |
| **Console.enable leak** | Patchright disables Console API |
| **navigator.webdriver** | Patchright removes --enable-automation flag |
| **Canvas fingerprint** | Real canvas with Xvfb |
| **Behavioral detection** | Human-like mouse via PyAutoGUI |

### Bot Detection Test Sites

- https://bot.sannysoft.com/
- https://abrahamjuliot.github.io/creepjs/
- https://pixelscan.net/
- https://bot.incolumitas.com/
- https://arh.antoinevastel.com/bots/areyouheadless

---

## CAPTCHA Solver

### Supported CAPTCHAs

| Type | Detection | Solving Method |
|------|-----------|----------------|
| **Cloudflare Turnstile** | iframe[src*="challenges.cloudflare.com"] | PyAutoGUI click checkbox |
| **hCaptcha** | .h-captcha element | PyAutoGUI + OCR for image selection |
| **reCAPTCHA v2** | .g-recaptcha element | PyAutoGUI click + audio fallback |

### Solving Flow

```
1. Detect CAPTCHA iframe/element
2. Take screenshot
3. Template matching or OCR to find button
4. Generate human-like mouse path
5. Click with random offset
6. Wait for verification
7. Retry if failed (max 3 attempts)
```

### Human-Like Mouse Movement

```python
def human_move(target: tuple):
    """Bezier-curve mouse movement with random deviation."""
    current = pyautogui.position()
    steps = random.randint(20, 40)
    
    for i in range(steps):
        progress = i / steps
        # Add randomness to path
        offset = random.randint(-5, 5) * (1 - progress)
        x = int(current[0] + (target[0] - current[0]) * progress + offset)
        y = int(current[1] + (target[1] - current[1]) * progress + offset)
        pyautogui.moveTo(x, y)
        time.sleep(random.uniform(0.001, 0.01))
    
    # Final click with small random offset
    pyautogui.click(target[0] + random.randint(-3, 3), 
                    target[1] + random.randint(-3, 3))
```

---

## Data Cleanup (Phase 5)

### Content Extraction Strategy

```python
def extract_clean_content(html: str, url: str) -> ExtractedContent:
    """
    Extract only relevant content, not full page source.
    
    1. Use trafilatura/readability for main content
    2. Remove: ads, navigation, footers, sidebars
    3. Extract: title, main text, images (optional)
    4. Summarize if > 1000 words
    5. Return structured clean data
    """
    import trafilatura
    
    # Extract main content
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False,
        no_fallback=False
    )
    
    # Clean up
    text = remove_boilerplate(text)
    text = normalize_whitespace(text)
    
    # Summarize if long
    summary = summarize(text) if len(text.split()) > 1000 else None
    
    return ExtractedContent(
        title=extract_title(downloaded),
        url=url,
        content=text[:5000],  # Cap at 5000 chars
        summary=summary,
        word_count=len(text.split())
    )
```

### Filtering Rules

| Remove | Keep |
|--------|------|
| Navigation menus | Article body |
| Sidebars | Blog post content |
| Footers | Product descriptions |
| Cookie banners | Prices/specs |
| Ad blocks | Reviews |
| Social share buttons | Tables (if relevant) |

---

## Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.12-slim

# Install Xvfb + GUI dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    x11-utils \
    xdotool \
    scrot \
    python3-tk \
    python3-dev \
    libx11-dev \
    libxtst-dev \
    libxext-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Patchright Chrome
RUN patchright install chrome

# Create non-root user
RUN useradd -m -s /bin/bash scraper
USER scraper
WORKDIR /home/scraper

COPY src/ ./src/
COPY templates/ ./templates/
COPY entrypoint.sh .

EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
```

### requirements.txt

```
patchright>=0.1.0
mcp[cli]>=2.0.0
pyautogui>=0.9.54
pillow>=10.0.0
pytesseract>=0.3.10
opencv-python-headless>=4.8.0
trafilatura>=1.6.0
pydantic>=2.0.0
```

### entrypoint.sh

```bash
#!/bin/bash

# Start Xvfb on display :99
Xvfb :99 -screen 0 1920x1080x24 -ac &
export DISPLAY=:99

# Wait for Xvfb
sleep 2

# Run MCP server
exec python -m src.server --transport streamable-http --port 8080
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  brave-scraper-mcp:
    build: .
    container_name: brave-scraper-mcp
    ports:
      - "8080:8080"
    volumes:
      - browser_data:/home/scraper/browser_data
    environment:
      - DISPLAY=:99
      - STEALTH_MODE=true
      - CAPTCHA_AUTO_SOLVE=true
    restart: unless-stopped
    cap_add:
      - SYS_ADMIN
    security_opt:
      - seccomp=unconfined

volumes:
  browser_data:
```

---

## Integration with mcporter

### Configuration

```bash
# Add to mcporter config
mcporter config add brave-scraper --url http://brave-scraper-mcp:8080/mcp
```

### Usage Examples

```bash
# Search Brave
mcporter call brave-scraper.brave_search query="python async" count:5

# Extract content from URL
mcporter call brave-scraper.brave_extract url="https://example.com/article"

# Navigate and screenshot
mcporter call brave-scraper.browser_navigate url="https://example.com"
mcporter call brave-scraper.browser_screenshot name="homepage"
```

---

## Testing Strategy (Phase 6)

### Unit Tests

| Test | Target | Success Criteria |
|------|--------|------------------|
| Bot detection bypass | bot.sannysoft.com | All green checks |
| Fingerprint evasion | creepjs | Trust score > 90% |
| Headless detection | pixelscan | "Native" rating |

### Integration Tests

| Test | Target | Success Criteria |
|------|--------|------------------|
| Cloudflare bypass | Various CF-protected sites | No challenge page |
| CAPTCHA solving | Turnstile test page | Auto-solve < 10s |
| Brave Search | search.brave.com | Returns structured results |

### Performance Tests

| Metric | Target |
|--------|--------|
| Browser startup | < 3s |
| Page load | < 5s |
| Search + extract | < 10s total |
| Memory usage | < 500MB idle |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISPLAY` | `:99` | Xvfb display |
| `STEALTH_MODE` | `true` | Enable stealth features |
| `CAPTCHA_AUTO_SOLVE` | `true` | Auto-solve CAPTCHAs |
| `BROWSER_PERSISTENT` | `true` | Keep browser open |
| `USER_DATA_DIR` | `/home/scraper/browser_data` | Browser profile location |
| `MAX_CONTENT_LENGTH` | `5000` | Max chars to return |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout |

---

## Implementation Phases

See **Task #35** in Status Tracker for detailed todos:

1. **Phase 1:** Core MCP Server
2. **Phase 2:** Stealth Layer
3. **Phase 3:** CAPTCHA Solver
4. **Phase 4:** Brave Search Tools
5. **Phase 5:** Data Cleanup
6. **Phase 6:** Testing
7. **Phase 7:** Docker Deployment

---

## References

- [Patchright Python](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Puppeteer MCP Server (archived)](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/puppeteer)
- [Trafilatura](https://trafilatura.readthedocs.io/)
