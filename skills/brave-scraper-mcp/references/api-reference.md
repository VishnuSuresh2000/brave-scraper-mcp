# Brave Scraper MCP Server API Reference

> **NO API KEY REQUIRED** - Uses browser automation with stealth features.

## Server Architecture

The Brave Scraper MCP server is a Python-based MCP server using:
- **Patchright** for browser automation (stealth mode)
- **Xvfb** for headless display
- **PyAutoGUI** for CAPTCHA solving
- **MCP Python SDK** for protocol handling

## Docker Configuration

```yaml
# docker-compose.yml
services:
  brave-scraper-mcp:
    build: .
    ports:
      - "8080:8080"
    networks:
      - traefik
    environment:
      - DISPLAY=:99
```

## MCP Protocol Details

### Transport: HTTP with SSE

The server uses HTTP transport with Server-Sent Events (SSE) for streaming responses.

**Key Requirements:**
1. Always include trailing slash: `/mcp/` not `/mcp`
2. Accept header must include both: `application/json, text/event-stream`
3. Content-Type: `application/json`

### Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "param1": "value1"
    }
  },
  "id": 1
}
```

### Response Format

```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"..."}]}}
```

## Tool Schemas

### brave_search

```json
{
  "name": "brave_search",
  "description": "Search Brave Search and return structured results. Includes AI-generated summary when Brave provides one (in ai_summary.text), along with cited sources",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Search query string"},
      "count": {"type": "integer", "default": 10, "minimum": 1, "maximum": 20},
      "page": {"type": "integer", "default": 1, "minimum": 1, "maximum": 10},
      "session_id": {"type": "string", "description": "Sub-agent session ID"}
    },
    "required": ["query"]
  }
}
```

### brave_extract

```json
{
  "name": "brave_extract",
  "description": "Extract clean, readable content from a URL",
  "inputSchema": {
    "type": "object",
    "properties": {
      "url": {"type": "string", "description": "URL to extract content from"},
      "max_length": {"type": "integer", "default": 5000},
      "session_id": {"type": "string", "description": "Sub-agent session ID"}
    },
    "required": ["url"]
  }
}
```

### brave_scrape_page

```json
{
  "name": "brave_scrape_page",
  "description": "Deep page scraper - full content as clean Markdown optimized for AI consumption",
  "inputSchema": {
    "type": "object",
    "properties": {
      "url": {"type": "string", "description": "URL to scrape"},
      "include_images": {"type": "boolean", "default": false},
      "session_id": {"type": "string", "description": "Sub-agent session ID"}
    },
    "required": ["url"]
  }
}
```

### browser_navigate

```json
{
  "name": "browser_navigate",
  "description": "Navigate browser to specified URL",
  "inputSchema": {
    "type": "object",
    "properties": {
      "url": {"type": "string"},
      "wait_until": {"type": "string", "enum": ["load", "domcontentloaded", "networkidle"], "default": "load"}
    },
    "required": ["url"]
  }
}
```

### browser_back

```json
{
  "name": "browser_back",
  "description": "Navigate back in browser history",
  "inputSchema": {"type": "object", "properties": {}}
}
```

### browser_screenshot

```json
{
  "name": "browser_screenshot",
  "description": "Capture screenshot of page or element",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {"type": "string", "description": "Screenshot filename"},
      "selector": {"type": "string", "description": "CSS selector for element"},
      "full_page": {"type": "boolean", "default": false}
    },
    "required": ["name"]
  }
}
```

### browser_click

```json
{
  "name": "browser_click",
  "description": "Click on element matching selector",
  "inputSchema": {
    "type": "object",
    "properties": {"selector": {"type": "string"}},
    "required": ["selector"]
  }
}
```

### browser_fill

```json
{
  "name": "browser_fill",
  "description": "Fill input field with value",
  "inputSchema": {
    "type": "object",
    "properties": {
      "selector": {"type": "string"},
      "value": {"type": "string"}
    },
    "required": ["selector", "value"]
  }
}
```

### browser_hover

```json
{
  "name": "browser_hover",
  "description": "Hover over element matching selector",
  "inputSchema": {
    "type": "object",
    "properties": {"selector": {"type": "string"}},
    "required": ["selector"]
  }
}
```

### browser_evaluate

```json
{
  "name": "browser_evaluate",
  "description": "Execute JavaScript in browser context",
  "inputSchema": {
    "type": "object",
    "properties": {"script": {"type": "string"}},
    "required": ["script"]
  }
}
```

### browser_solve_captcha

```json
{
  "name": "browser_solve_captcha",
  "description": "Auto-detect and solve CAPTCHA challenges",
  "inputSchema": {
    "type": "object",
    "properties": {"timeout": {"type": "integer", "default": 30}}
  }
}
```

## Search Result Structure

```json
[
  {
    "title": "Result Title",
    "url": "https://example.com/page",
    "snippet": "Brief description...",
    "site": "example.com"
  }
]
```

## Performance Notes

- Search queries: 15-30 seconds (browser automation)
- Content extraction: 5-10 seconds
- CAPTCHA solving: Adds 5-15 seconds if triggered

## CAPTCHA Support

The server automatically handles:
- **Cloudflare Turnstile**: Checkbox clicking
- **hCaptcha**: Image selection (limited)
- **reCAPTCHA v2**: Checkbox + image challenges
- **Slider CAPTCHAs**: Human-like drag simulation

## Stealth Features

- Patchright browser with undetected patches
- Randomized mouse movements
- Human-like typing delays
- Canvas fingerprint randomization
