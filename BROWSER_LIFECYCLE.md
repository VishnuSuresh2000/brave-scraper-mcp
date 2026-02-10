# Browser Lifecycle Management

The Brave Scraper MCP server implements a robust browser lifecycle management system to handle concurrent requests from both the Main Agent and multiple Sub-Agents.

## Architecture

### 1. Main Agent Requests
- **Pattern**: Shared Browser Process + Isolated Contexts.
- **Concurrency**: Handled via `BrowserManager.isolated_context()`.
- **Locking**: A request-level lock (`asyncio.Lock`) is held for the **entire duration** of navigation and extraction to prevent race conditions in the shared Chromium process.
- **Isolation**: Each request gets a fresh Playwright `BrowserContext` (Incognito) which is closed immediately after use.

### 2. Sub-Agent Sessions
- **Pattern**: Dedicated Browser Processes per Sub-Agent.
- **Management**: Handled by `SubAgentBrowserManager`.
- **Tab Limit**: Each sub-agent is limited to **15 concurrent tabs**. Older tabs are evicted using an **LRU (Least Recently Used)** strategy.
- **Auto-Cleanup**: Inactive browser processes are automatically closed after an idle timeout (default: 30 minutes, configurable via `BROWSER_TIMEOUT_MINUTES`).
- **Isolation**: High. Sub-agents do not share browser processes or contexts with each other or the main agent.

## Configuration

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `BROWSER_TIMEOUT_MINUTES` | 30 | Minutes of inactivity before a sub-agent browser is cleaned up. |

## Tool Integration

Both `brave_search` and `brave_extract` tools support an optional `session_id`.
- If `session_id` is provided (format: `sub-agent-{id}`), the tool uses the dedicated sub-agent browser.
- If no `session_id` is provided, the tool uses the shared main browser with request-level locking.

## Monitoring & Stats

The `BrowserManager` provides stats on active sessions and tab usage:
- `active_sessions`: Number of active sub-agent browser processes.
- `tab_count`: Number of open tabs in a specific session.
- `idle_seconds`: Time since last activity in a session.
