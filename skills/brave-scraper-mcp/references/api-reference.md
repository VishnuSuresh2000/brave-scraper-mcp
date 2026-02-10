# Brave Search MCP Server API Reference

## Server Architecture

The Brave Search MCP server is a Python-based MCP server using:
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
  "description": "Search Brave Search and return structured results",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query string"
      },
      "count": {
        "type": "integer",
        "default": 10,
        "description": "Number of results to return"
      }
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
      "url": {
        "type": "string",
        "description": "URL to extract content from"
      },
      "max_length": {
        "type": "integer",
        "default": 5000,
        "description": "Maximum content length in characters"
      }
    },
    "required": ["url"]
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
