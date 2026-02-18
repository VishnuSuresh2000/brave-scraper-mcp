# Brave Scraper MCP Server

[![GitHub repo](https://img.shields.io/badge/github-repo-000?logo=github)](https://github.com/VishnuSuresh2000/brave-scraper-mcp)

A stealth web scraping MCP (Model Context Protocol) server using **Patchright** for undetected browsing, **Xvfb** for anti-headless detection, and **PyAutoGUI** for CAPTCHA bypass. Provides Brave Search integration with smart content extraction.

> **⚠️ NO API KEY REQUIRED** - This server uses a headless browser (Patchright) to scrape Brave Search directly. No API keys, no rate limits, no registration needed.

## Links

- **GitHub Repository**: https://github.com/VishnuSuresh2000/brave-scraper-mcp
- **Issues**: https://github.com/VishnuSuresh2000/brave-scraper-mcp/issues
- **Skill Documentation**: See `skills/brave-scraper-mcp/` for agent integration details.
- **Connecting Other MCP Clients**: `skills/brave-scraper-mcp/references/mcp-clients.md`

## Features

- 🕵️ **Stealth Mode**: Uses Patchright (undetected Playwright fork) + Xvfb to avoid bot detection
- 🔓 **CAPTCHA Solving**: Auto-detects and solves Cloudflare Turnstile, hCaptcha, and reCAPTCHA
- 📄 **Full Page Scraping**: Scrape any webpage and convert to clean Markdown
- 🔍 **Brave Search**: Search the web without API keys
- 🤖 **AI-Ready Extraction**: Content optimized for LLMs/RAG – clean, structured, no noise
- 📋 **AI Summary from Brave**: `brave_search` automatically extracts Brave's own AI-generated summary (when available) and cited sources

## Server URL

```
http://brave-scraper-mcp:8080/mcp
```

**Health Check:** `http://brave-scraper-mcp:8080/health`

## Available Tools

| Tool | Description |
|------|-------------|
| `brave_search` | Search Brave Search (no API key needed). **Returns AI summary** if Brave generates one, plus cited sources |
| `brave_extract` | Extract clean content from URL |
| `brave_scrape_page` | Scrape full page as Markdown |
| `browser_navigate` | Navigate to a URL |
| `browser_back` | Navigate back in history |
| `browser_screenshot` | Capture page/element screenshot |
| `browser_click` | Click an element |
| `browser_fill` | Fill input field |
| `browser_hover` | Hover over element |
| `browser_evaluate` | Execute JavaScript |
| `browser_solve_captcha` | Auto-solve CAPTCHA challenges |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) [mcporter](https://github.com/openclaw/mcporter) for MCP integration

### 1. Clone and Build

```bash
git clone https://github.com/VishnuSuresh2000/brave-scraper-mcp.git
cd brave-scraper-mcp
docker compose up -d --build
```

### 2. Verify Deployment

```bash
# Check container health
docker ps

# Test health endpoint
curl http://localhost:8080/health
# Expected: {"status": "healthy", "server": "brave-scraper-mcp"}
```

### 3. Configure mcporter (Optional)

```bash
# Add to mcporter config
mcporter config add brave-scraper --url http://localhost:8080/mcp

# List available tools
mcporter list brave-scraper
```

## Using with OpenClaw Agents

This server provides MCP tools that can be installed as a **skill** in OpenClaw agents. Skills extend agent capabilities; you can install this skill via local copy or mcporter.

### Installation Methods

#### Local Installation (Manual)

Copy the skill folder to your agent's workspace or global skills directory:

```bash
# Workspace-specific (preferred)
cp -r skills/brave-scraper-mcp ~/.openclaw/workspace/your-agent/skills/

# Global (available to all agents)
cp -r skills/brave-scraper-mcp ~/.openclaw/skills/
```

#### MCP Server Import (mcporter)

Add the running server as an MCP source:

```bash
mcporter config add brave-scraper --url http://localhost:8080/mcp
```

Then import into OpenClaw:

```bash
mcporter config import opencode --copy
```

### Verification

Check that the skill is eligible and tools are available:

```bash
openclaw skills list --eligible
openclaw skills info brave-scraper-mcp
```

### Documentation

- **OpenClaw Agent Concepts**: [docs/concepts/agent.md](https://github.com/openclaw/openclaw/blob/main/docs/concepts/agent.md)
- **MCP Integration (mcporter)**: [docs/tools/mcporter.md](https://github.com/openclaw/openclaw/blob/main/docs/tools/mcporter.md)
- **Multi-Agent Setup**: [docs/concepts/multi-agent.md](https://github.com/openclaw/openclaw/blob/main/docs/concepts/multi-agent.md)
- **Multi-Agent Setup**: [docs/concepts/multi-agent.md](https://github.com/openclaw/openclaw/blob/main/docs/concepts/multi-agent.md)

## Usage Examples

### Via mcporter CLI

```bash
# Search Brave
mcporter call brave-scraper.brave_search query="python async programming" count:5

# Extract content from URL
mcporter call brave-scraper.brave_extract url="https://example.com/article"

# Navigate and screenshot
mcporter call brave-scraper.browser_navigate url="https://example.com"
mcporter call brave-scraper.browser_screenshot name="homepage"
```

### Via MCP Client (Agent Integration)

The server exposes tools via the MCP protocol at `/mcp` endpoint. Connect your MCP client to:

```
http://localhost:8080/mcp
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISPLAY` | `:99` | Xvfb display |
| `STEALTH_MODE` | `true` | Enable stealth features |
| `CAPTCHA_AUTO_SOLVE` | `true` | Auto-solve CAPTCHAs |
| `PORT` | `8080` | Server port |
| `MAX_CONTENT_LENGTH` | `5000` | Max content chars to return |
| `REQUEST_TIMEOUT` | `30` | HTTP timeout seconds |

### Docker Compose

```yaml
services:
  brave-scraper-mcp:
    build: .
    ports:
      - "8080:8080"
    environment:
      - STEALTH_MODE=true
      - CAPTCHA_AUTO_SOLVE=true
    volumes:
      - browser_data:/home/scraper/browser_data
    cap_add:
      - SYS_ADMIN
    security_opt:
      - seccomp=unconfined
```

## Development

### Local Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Install Patchright Chrome
patchright install chrome

# Run server (stdio mode)
python -m src.server

# Run server (HTTP mode)
python -m src.server --transport streamable-http --port 8080
```

### Running Tests

```bash
# Activate venv
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src
```

## Architecture

```
brave-scraper-mcp/
├── src/
│   ├── server.py           # MCP server entry point
│   ├── browser/
│   │   ├── manager.py      # Browser lifecycle
│   │   ├── stealth.py      # Xvfb + anti-detection
│   │   └── captcha.py      # CAPTCHA solving
│   └── tools/
│       ├── navigation.py   # browser_navigate, browser_back
│       ├── interaction.py  # browser_click, browser_fill
│       ├── extraction.py   # browser_screenshot, browser_evaluate
│       └── brave_search.py # brave_search, brave_extract
├── templates/              # CAPTCHA element templates
├── tests/                  # Unit and integration tests
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
└── requirements.txt
```

## Anti-Detection Features

| Feature | Implementation |
|---------|----------------|
| Headless detection | Xvfb + headful Chrome |
| Runtime.enable leak | Patchright isolated contexts |
| navigator.webdriver | Patchright removes flag |
| Canvas fingerprint | Real canvas with Xvfb |
| Behavioral detection | Human-like mouse via PyAutoGUI |

## CAPTCHA Support

| Type | Detection | Solving Method |
|------|-----------|----------------|
| Cloudflare Turnstile | iframe selector | PyAutoGUI click |
| hCaptcha | .h-captcha element | PyAutoGUI + OCR |
| reCAPTCHA v2 | .g-recaptcha element | Click + audio fallback |

## Security Notes

- Container runs as non-root user `scraper`
- No API keys stored in image
- Browser data persisted in Docker volume
- Recommended: Use network isolation in production

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs brave-scraper-mcp

# Common issues:
# - Xvfb lock file: Remove /tmp/.X99-lock
# - Port in use: Change PORT in docker-compose.yml
```

### MCP connection fails

```bash
# Verify endpoint
curl http://localhost:8080/health

# Check mcporter config
mcporter list brave-scraper
```

### Bot detection

- Ensure `STEALTH_MODE=true`
- Check Xvfb is running: `docker exec brave-scraper-mcp ps aux | grep Xvfb`
- Test at https://bot.sannysoft.com/

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## Acknowledgments

- [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python) - Undetected Playwright
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - MCP implementation
- [Trafilatura](https://trafilatura.readthedocs.io/) - Content extraction
