# Connecting Brave Scraper MCP to Various Clients

The Brave Scraper MCP server is a standard MCP server and can be used with any MCP-compatible client. This guide covers popular clients.

## Common Server Endpoint

```
http://localhost:8080/mcp/
```

**Important:** Include the trailing slash (`/mcp/` not `/mcp`).

Required headers when making direct HTTP calls:
- `Accept: application/json, text/event-stream`
- `Content-Type: application/json`

---

## OpenClaw (OpenCode / Cloud Code CLI)

### Using mcporter (recommended)

```bash
mcporter config add brave-scraper --url http://localhost:8080/mcp
mcporter config import opencode --copy
```

### Manual configuration

Edit `~/.openclaw/config/mcp.json` (or use command palette):
```json
{
  "mcpServers": {
    "brave-scraper": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

---

## Cursor IDE

1. Open Cursor Settings → `MCP` tab
2. Click `Add Server`
3. Name: `brave-scraper`
4. Type: `HTTP`
5. URL: `http://localhost:8080/mcp`
6. Save

Alternatively, edit `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "brave-scraper": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

---

## Claude Code Desktop

Claude Code Desktop doesn't yet support adding custom MCP servers via UI. Use **mcporter** as a bridge:

```bash
mcporter config add brave-scraper --url http://localhost:8080/mcp
mcporter config import claude
```

If that fails, you can start a session with Claude Code and manually add the server via its config file.

---

## Continue (VS Code Extension)

Add to Continue config (`~/.continue/config.json`):
```json
{
  "mcpServers": {
    "brave-scraper": {
      "url": "http://localhost:8080/mcp",
      "name": "Brave Scraper"
    }
  }
}
```

---

## Windsurf (by Codeium)

Windsurf supports MCP via config file:
```json
{
  "mcpServers": {
    "brave-scraper": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

---

## Generic MCP Client

For any MCP-compatible client, use:

```bash
curl -s -X POST http://localhost:8080/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
  }'
```

---

## Troubleshooting

- **Connection refused**: Ensure Docker container is running (`docker ps | grep brave-scraper-mcp`)
- **Network issues**: Server must be reachable from client (same host or forwarded port)
- **SSE errors**: Double-check trailing slash (`/mcp/`)
- **CORS**: Some clients enforce CORS; if using direct HTTP, ensure client allows it

For agent-specific issues, see the main `SKILL.md` and `AGENT_SETUP.md` in the skill folder.
