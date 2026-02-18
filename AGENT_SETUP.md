# Agent Setup Guide

This guide explains how to configure AI agents to use the Brave Scraper MCP server.

## Prerequisites

- Docker and Docker Compose installed
- Access to the `traefik` Docker network
- (Optional) [mcporter](https://github.com/openclaw/mcporter) CLI tool

## Quick Setup

### 1. Deploy the MCP Server

```bash
git clone https://github.com/YOUR_USERNAME/brave-scraper-mcp.git
cd brave-scraper-mcp
docker compose up -d --build
```

### 2. Verify Deployment

```bash
curl http://localhost:8080/health
# Expected: {"status": "healthy", "server": "brave-scraper-mcp"}
```

### 3. Configure mcporter (Optional)

```bash
mcporter config add brave-scraper --url http://brave-scraper-mcp:8080/mcp
mcporter list brave-scraper
```

## Agent Configuration

### For OpenCode Agents

Add to your agent's skill configuration:

```yaml
skills:
  - name: brave-scraper-mcp
    url: http://brave-scraper-mcp:8080/mcp
```

### For Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "brave-scraper-mcp": {
      "url": "http://brave-scraper-mcp:8080/mcp"
    }
  }
}
```

### For Other MCP Clients

Configure the MCP client to connect to:
```
http://brave-scraper-mcp:8080/mcp
```

## Network Requirements

The MCP server must be accessible from your agent's container:

1. **Same Docker Network**: Add your agent container to the `traefik` network
2. **Health Check**: Verify connectivity with `curl http://brave-scraper-mcp:8080/health`

```yaml
# docker-compose.yml for your agent
services:
  your-agent:
    # ...
    networks:
      - traefik

networks:
  traefik:
    external: true
```

## No API Key Required

This server uses browser automation (Patchright) to access Brave Search directly. No API keys or registration needed.

## Available Tools Summary

| Tool | Purpose |
|------|---------|
| `brave_search` | Web search via Brave |
| `brave_extract` | Extract clean content |
| `brave_scrape_page` | Full page as Markdown |
| `browser_navigate` | Navigate to URL |
| `browser_screenshot` | Capture screenshots |
| `browser_click` | Click elements |
| `browser_fill` | Fill form inputs |
| `browser_hover` | Hover over elements |
| `browser_evaluate` | Run JavaScript |
| `browser_solve_captcha` | Solve CAPTCHAs |
| `browser_back` | Navigate back |

## Troubleshooting

### Connection Refused

```bash
# Check container status
docker ps | grep brave-scraper-mcp

# Check network connectivity
docker network inspect traefik
```

### Slow Responses

Browser automation takes 15-30 seconds for search queries. This is normal.

### Bot Detection

Ensure `STEALTH_MODE=true` in the container environment.
