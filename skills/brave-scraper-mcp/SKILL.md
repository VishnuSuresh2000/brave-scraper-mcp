---
name: brave-scraper-mcp
description: "Search the web and extract content using the Brave Search MCP server. NO API KEY REQUIRED. Use when you need to search for information, research topics, or extract readable content from URLs. Tools: brave_search, brave_extract, brave_scrape_page, browser_navigate, browser_screenshot, browser_click, browser_fill, browser_hover, browser_evaluate, browser_solve_captcha. Accessible at http://brave-scraper-mcp:8080/mcp from Docker networks."
---

# Brave Scraper MCP Server

Stealth web scraping via MCP protocol. NO API KEY REQUIRED - uses browser automation.

## MCP Server Location

- **URL**: `http://brave-scraper-mcp:8080/mcp`
- **Health Check**: `http://brave-scraper-mcp:8080/health`
- **Network**: Must be on `traefik` Docker network

## Using with mcporter CLI

### Configure mcporter

```bash
mcporter config add brave-scraper --url http://brave-scraper-mcp:8080/mcp
```

### Search the Web

```bash
mcporter call brave-scraper.brave_search query="your search query"
```

```bash
mcporter call brave-scraper.brave_search query="python async" count:5 page:1
```

**Parameters:**
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `count` | integer | No | 10 | Results (1-20) |
| `page` | integer | No | 1 | Page number (1-10) |
| `session_id` | string | No | - | Sub-agent session ID |

### Extract Content from URL

```bash
mcporter call brave-scraper.brave_extract url="https://example.com/article"
```

```bash
mcporter call brave-scraper.brave_extract url="https://example.com" max_length:10000
```

**Parameters:**
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | Yes | - | URL to extract |
| `max_length` | integer | No | 5000 | Max characters |
| `session_id` | string | No | - | Sub-agent session ID |

### Scrape Page as Markdown

```bash
mcporter call brave-scraper.brave_scrape_page url="https://example.com"
```

```bash
mcporter call brave-scraper.brave_scrape_page url="https://example.com" include_images:true
```

### Browser Automation

```bash
mcporter call brave-scraper.browser_navigate url="https://example.com"
mcporter call brave-scraper.browser_screenshot name="homepage" full_page:true
mcporter call brave-scraper.browser_click selector="button.submit"
mcporter call brave-scraper.browser_fill selector="input[name=email]" value="test@example.com"
mcporter call brave-scraper.browser_hover selector=".menu-item"
mcporter call brave-scraper.browser_evaluate script="document.title"
mcporter call brave-scraper.browser_solve_captcha timeout:30
mcporter call brave-scraper.browser_back
```

## Using via Raw curl (for sub-agents without mcporter)

### List Available Tools

```bash
curl -s -X POST http://brave-scraper-mcp:8080/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
```

### Call brave_search Tool

```bash
curl -s -X POST http://brave-scraper-mcp:8080/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "brave_search",
      "arguments": {
        "query": "your search query",
        "count": 10
      }
    },
    "id": 2
  }'
```

## Available Tools

| Tool | Description | Required Params | Optional Params |
|------|-------------|-----------------|-----------------|
| `brave_search` | Search Brave Search | `query` | `count`, `page`, `session_id` |
| `brave_extract` | Extract clean content | `url` | `max_length`, `session_id` |
| `brave_scrape_page` | Scrape page as Markdown | `url` | `include_images`, `session_id` |
| `browser_navigate` | Navigate to URL | `url` | `wait_until` |
| `browser_back` | Navigate back | - | - |
| `browser_screenshot` | Capture screenshot | `name` | `selector`, `full_page` |
| `browser_click` | Click element | `selector` | - |
| `browser_fill` | Fill input field | `selector`, `value` | - |
| `browser_hover` | Hover over element | `selector` | - |
| `browser_evaluate` | Execute JavaScript | `script` | - |
| `browser_solve_captcha` | Auto-solve CAPTCHA | - | `timeout` |

## Example: Research Workflow

```bash
mcporter call brave-scraper.brave_search query="REST API best practices" count:5
mcporter call brave-scraper.brave_extract url="https://example.com/api-guide"
mcporter call brave-scraper.brave_scrape_page url="https://example.com/docs" include_images:true
```

## Troubleshooting

### Connection Refused
- Ensure container is running: `docker ps | grep brave-scraper-mcp`
- Check network access: Container must be on `traefik` network

### No Search Results
- Server uses browser automation (15-30 seconds)
- CAPTCHA may be blocking (rare for Brave Search)

### MCP Protocol Errors
- Include both `Accept: application/json, text/event-stream` headers
- Use `tools/call` method with `name` and `arguments` object

## Agent Integration

This skill provides tools that can be installed into OpenClaw agents. For detailed setup instructions (local, mcporter), see:

- **references/agent-setup.md** – Agent configuration, skill installation, verification
- **references/mcp-clients.md** – Connect from Cursor, Claude Code, Cloud Code, and other MCP clients

**Note**: While the skill package is for OpenClaw, the underlying MCP server works with any MCP client. See `mcp-clients.md` for cross-client setup.
