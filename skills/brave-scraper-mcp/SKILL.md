---
name: brave-scraper-mcp
description: Search the web and extract content using the Brave Search MCP server. Use when you need to search for information, research topics, or extract readable content from URLs. Tools available: brave_search (web search), brave_extract (content extraction). The MCP server is accessible at http://brave-scraper-mcp:8080/mcp from Docker networks (including sandbox containers with traefik network access).
---

# Brave Search MCP Server

Access Brave Search via MCP protocol for web search and content extraction.

## MCP Server Location

- **URL**: `http://brave-scraper-mcp:8080/mcp`
- **Health Check**: `http://brave-scraper-mcp:8080/health`
- **Network**: Must be on `traefik` Docker network

## Using with mcporter CLI

### Search the Web

```bash
mcporter call http://brave-scraper-mcp:8080/mcp brave_search \
  --arg query="your search query" \
  --arg count=10
```

Parameters:
- `query` (required): Search query string
- `count` (optional): Number of results, default 10

Returns: JSON array of search results with title, url, snippet, site.

### Extract Content from URL

```bash
mcporter call http://brave-scraper-mcp:8080/mcp brave_extract \
  --arg url="https://example.com/article" \
  --arg max_length=5000
```

Parameters:
- `url` (required): URL to extract content from
- `max_length` (optional): Max characters, default 5000

Returns: Clean, readable text content from the page.

## Using via Raw curl (for sub-agents without mcporter)

Sub-agents in sandbox containers can use curl with MCP JSON-RPC protocol:

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

**Note**: The server uses SSE (Server-Sent Events), so requests may take 15-30 seconds.

### Call brave_extract Tool

```bash
curl -s -X POST http://brave-scraper-mcp:8080/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "brave_extract",
      "arguments": {
        "url": "https://example.com",
        "max_length": 5000
      }
    },
    "id": 3
  }'
```

## Available Tools

| Tool | Description | Required Params | Optional Params |
|------|-------------|-----------------|-----------------|
| `brave_search` | Search Brave Search | `query` | `count` (default: 10) |
| `brave_extract` | Extract clean content | `url` | `max_length` (default: 5000) |
| `browser_navigate` | Navigate browser | `url` | `wait_until` |
| `browser_screenshot` | Take screenshot | `name` | `selector`, `full_page` |
| `browser_click` | Click element | `selector` | - |
| `browser_fill` | Fill input | `selector`, `value` | - |
| `browser_solve_captcha` | Auto-solve CAPTCHA | - | `timeout` |

## Example: Research Workflow

```bash
# 1. Search for information
mcporter call http://brave-scraper-mcp:8080/mcp brave_search \
  --arg query="best practices for REST API design" \
  --arg count=5

# 2. Extract content from top result
mcporter call http://brave-scraper-mcp:8080/mcp brave_extract \
  --arg url="https://example.com/api-guide"

# 3. Get structured content for analysis
```

## Troubleshooting

### Connection Refused
- Ensure container is running: `docker ps | grep brave-scraper-mcp`
- Check network access: Container must be on `traefik` network

### No Search Results
- The server uses browser automation, may take 15-30 seconds
- Check if CAPTCHA is blocking (rare for Brave Search)

### MCP Protocol Errors
- Always include both `Accept: application/json, text/event-stream` headers
- Use `tools/call` method with `name` and `arguments` object
