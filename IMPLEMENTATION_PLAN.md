# Phase 1: Core MCP Server - Implementation Plan

## Overview
Build the foundational MCP server with basic browser automation capabilities using Patchright + MCP Python SDK v2.

---

## 1. File Structure

```
stealth-browser-mcp/
├── src/
│   ├── __init__.py
│   ├── server.py              # Main MCP server entry
│   ├── browser/
│   │   ├── __init__.py
│   │   └── manager.py         # Browser lifecycle (Phase 1: basic)
│   └── tools/
│       ├── __init__.py
│       ├── navigation.py      # browser_navigate, browser_back
│       ├── interaction.py     # browser_click, browser_fill, browser_hover
│       └── extraction.py      # browser_screenshot, browser_evaluate
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # pytest fixtures
│   └── test_server.py         # Server initialization tests
├── requirements.txt
└── pyproject.toml             # Python project config
```

---

## 2. Dependencies

### requirements.txt
```
# MCP Framework
mcp[cli]>=2.0.0

# Browser Automation
patchright>=0.1.0

# Data Validation
pydantic>=2.0.0

# Async Support (for MCP)
anyio>=4.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

### Key Dependency Notes
- **mcp[cli]>=2.0.0**: Provides `@mcp.tool()` decorator pattern
- **patchright>=0.1.0**: Undetected Playwright fork for stealth
- **pydantic>=2.0.0**: Type validation for tool parameters

---

## 3. Core Implementation

### 3.1 Server Entry Point (`src/server.py`)

```python
#!/usr/bin/env python3
"""
Stealth Browser MCP Server - Phase 1: Core Server
MCP server with basic browser automation tools.
"""

import asyncio
import logging
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.browser.manager import BrowserManager
from src.tools.navigation import NavigationTools
from src.tools.interaction import InteractionTools
from src.tools.extraction import ExtractionTools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stealth-browser-mcp")


class StealthBrowserServer:
    """MCP Server for Stealth Browser with web scraping capabilities."""
    
    def __init__(self):
        self.server = Server("stealth-browser-mcp")
        self.browser_manager: Optional[BrowserManager] = None
        self.nav_tools: Optional[NavigationTools] = None
        self.interact_tools: Optional[InteractionTools] = None
        self.extract_tools: Optional[ExtractionTools] = None
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Register MCP tool handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            return [
                # Navigation Tools
                Tool(
                    name="browser_navigate",
                    description="Navigate browser to specified URL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to navigate to"},
                            "wait_until": {
                                "type": "string",
                                "enum": ["load", "domcontentloaded", "networkidle"],
                                "default": "load",
                                "description": "When to consider navigation complete"
                            }
                        },
                        "required": ["url"]
                    }
                ),
                Tool(
                    name="browser_back",
                    description="Navigate back in browser history",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                
                # Interaction Tools
                Tool(
                    name="browser_click",
                    description="Click on element matching selector",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for element"}
                        },
                        "required": ["selector"]
                    }
                ),
                Tool(
                    name="browser_fill",
                    description="Fill input field with value",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for input"},
                            "value": {"type": "string", "description": "Value to fill"}
                        },
                        "required": ["selector", "value"]
                    }
                ),
                Tool(
                    name="browser_hover",
                    description="Hover over element matching selector",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for element"}
                        },
                        "required": ["selector"]
                    }
                ),
                
                # Extraction Tools
                Tool(
                    name="browser_screenshot",
                    description="Capture screenshot of page or element",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Screenshot filename"},
                            "selector": {"type": "string", "description": "Optional: CSS selector for element"},
                            "full_page": {"type": "boolean", "default": False, "description": "Capture full page"}
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="browser_evaluate",
                    description="Execute JavaScript in browser context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "script": {"type": "string", "description": "JavaScript code to execute"}
                        },
                        "required": ["script"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Execute tool by name."""
            logger.info(f"Calling tool: {name} with args: {arguments}")
            
            if not self.browser_manager or not self.browser_manager.page:
                return [TextContent(type="text", text="Error: Browser not initialized")]
            
            try:
                result = await self._execute_tool(name, arguments)
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _execute_tool(self, name: str, arguments: dict) -> str:
        """Route tool call to appropriate handler."""
        page = self.browser_manager.page
        
        # Navigation tools
        if name == "browser_navigate":
            await page.goto(arguments["url"], wait_until=arguments.get("wait_until", "load"))
            return f"Navigated to {arguments['url']}"
        
        elif name == "browser_back":
            await page.go_back()
            return "Navigated back"
        
        # Interaction tools
        elif name == "browser_click":
            await page.click(arguments["selector"])
            return f"Clicked element: {arguments['selector']}"
        
        elif name == "browser_fill":
            await page.fill(arguments["selector"], arguments["value"])
            return f"Filled {arguments['selector']} with value"
        
        elif name == "browser_hover":
            await page.hover(arguments["selector"])
            return f"Hovered over {arguments['selector']}"
        
        # Extraction tools
        elif name == "browser_screenshot":
            path = f"/tmp/{arguments['name']}.png"
            if arguments.get("selector"):
                element = await page.query_selector(arguments["selector"])
                if element:
                    await element.screenshot(path=path)
                else:
                    return f"Element not found: {arguments['selector']}"
            else:
                await page.screenshot(path=path, full_page=arguments.get("full_page", False))
            return f"Screenshot saved: {path}"
        
        elif name == "browser_evaluate":
            result = await page.evaluate(arguments["script"])
            return str(result)
        
        else:
            return f"Unknown tool: {name}"
    
    async def initialize(self):
        """Initialize browser manager."""
        logger.info("Initializing browser manager...")
        self.browser_manager = BrowserManager()
        await self.browser_manager.start()
        logger.info("Browser manager initialized")
    
    async def cleanup(self):
        """Cleanup browser resources."""
        if self.browser_manager:
            await self.browser_manager.stop()
            logger.info("Browser manager stopped")
    
    async def run(self):
        """Run the MCP server."""
        await self.initialize()
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            await self.cleanup()


async def main():
    """Entry point."""
    server = StealthBrowserServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### 3.2 Browser Manager (`src/browser/manager.py`)

```python
"""
Browser lifecycle management using Patchright.
Phase 1: Basic browser initialization without stealth features.
"""

import os
import logging
from typing import Optional

import patchright
from patchright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser lifecycle with Patchright."""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.user_data_dir = os.getenv("USER_DATA_DIR", "/tmp/browser_data")
    
    async def start(self):
        """Start browser instance."""
        logger.info("Starting browser...")
        
        self.playwright = await async_playwright().start()
        
        # Phase 1: Basic launch (stealth in Phase 2)
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # Will change to False in Phase 2 with Xvfb
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        
        self.page = await self.context.new_page()
        
        logger.info("Browser started successfully")
    
    async def stop(self):
        """Stop browser and cleanup resources."""
        logger.info("Stopping browser...")
        
        if self.page:
            await self.page.close()
        
        if self.context:
            await self.context.close()
        
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        logger.info("Browser stopped")
    
    async def new_page(self) -> Page:
        """Create a new page in the context."""
        if not self.context:
            raise RuntimeError("Browser not initialized")
        return await self.context.new_page()
```

### 3.3 Tool Modules

**`src/tools/navigation.py`:**
```python
"""Navigation tool implementations."""
from patchright.async_api import Page


class NavigationTools:
    """Tools for browser navigation."""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def navigate(self, url: str, wait_until: str = "load") -> str:
        """Navigate to URL."""
        await self.page.goto(url, wait_until=wait_until)
        return f"Navigated to {url}"
    
    async def go_back(self) -> str:
        """Navigate back in history."""
        await self.page.go_back()
        return "Navigated back"
    
    async def reload(self) -> str:
        """Reload current page."""
        await self.page.reload()
        return "Page reloaded"
```

**`src/tools/interaction.py`:**
```python
"""Interaction tool implementations."""
from patchright.async_api import Page


class InteractionTools:
    """Tools for DOM interaction."""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def click(self, selector: str) -> str:
        """Click element."""
        await self.page.click(selector)
        return f"Clicked: {selector}"
    
    async def fill(self, selector: str, value: str) -> str:
        """Fill input field."""
        await self.page.fill(selector, value)
        return f"Filled {selector}"
    
    async def hover(self, selector: str) -> str:
        """Hover over element."""
        await self.page.hover(selector)
        return f"Hovered: {selector}"
    
    async def scroll(self, x: int = 0, y: int = 0) -> str:
        """Scroll page."""
        await self.page.evaluate(f"window.scrollBy({x}, {y})")
        return f"Scrolled by ({x}, {y})"
```

**`src/tools/extraction.py`:**
```python
"""Extraction tool implementations."""
import base64
from patchright.async_api import Page


class ExtractionTools:
    """Tools for content extraction."""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def screenshot(
        self, 
        name: str, 
        selector: str = None, 
        full_page: bool = False
    ) -> str:
        """Capture screenshot."""
        path = f"/tmp/{name}.png"
        
        if selector:
            element = await self.page.query_selector(selector)
            if not element:
                raise ValueError(f"Element not found: {selector}")
            await element.screenshot(path=path)
        else:
            await self.page.screenshot(path=path, full_page=full_page)
        
        return path
    
    async def evaluate(self, script: str) -> any:
        """Execute JavaScript and return result."""
        return await self.page.evaluate(script)
    
    async def get_text(self, selector: str = None) -> str:
        """Extract text content."""
        if selector:
            element = await self.page.query_selector(selector)
            if not element:
                return ""
            return await element.text_content()
        return await self.page.evaluate("document.body.innerText")
    
    async def get_html(self) -> str:
        """Get page HTML."""
        return await self.page.content()
```

---

## 4. Project Configuration

### 4.1 pyproject.toml
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "stealth-browser-mcp"
version = "0.1.0"
description = "MCP server for stealth web scraping"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
dependencies = [
    "mcp[cli]>=2.0.0",
    "patchright>=0.1.0",
    "pydantic>=2.0.0",
    "anyio>=4.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
stealth-browser-mcp = "src.server:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
select = ["E", "F", "I"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### 4.2 __init__.py Files

**`src/__init__.py`:**
```python
"""Stealth Browser MCP Server."""
__version__ = "0.1.0"
```

**`src/browser/__init__.py`:**
```python
"""Browser automation components."""
from src.browser.manager import BrowserManager

__all__ = ["BrowserManager"]
```

**`src/tools/__init__.py`:**
```python
"""MCP tool implementations."""
from src.tools.navigation import NavigationTools
from src.tools.interaction import InteractionTools
from src.tools.extraction import ExtractionTools

__all__ = ["NavigationTools", "InteractionTools", "ExtractionTools"]
```

---

## 5. Testing

### 5.1 Test Configuration (`tests/conftest.py`)
```python
"""pytest fixtures."""
import pytest
import pytest_asyncio

from src.browser.manager import BrowserManager


@pytest_asyncio.fixture
async def browser_manager():
    """Browser manager fixture."""
    manager = BrowserManager()
    await manager.start()
    yield manager
    await manager.stop()
```

### 5.2 Server Tests (`tests/test_server.py`)
```python
"""Tests for MCP server."""
import pytest
from src.server import StealthBrowserServer


class TestServerInitialization:
    """Test server setup and initialization."""
    
    @pytest.mark.asyncio
    async def test_server_creates_instance(self):
        """Server instance can be created."""
        server = StealthBrowserServer()
        assert server is not None
        assert server.server is not None
    
    @pytest.mark.asyncio
    async def test_browser_initialization(self, browser_manager):
        """Browser manager initializes correctly."""
        assert browser_manager.browser is not None
        assert browser_manager.context is not None
        assert browser_manager.page is not None
    
    @pytest.mark.asyncio
    async def test_navigation_tools(self, browser_manager):
        """Navigation tools work."""
        from src.tools.navigation import NavigationTools
        
        nav = NavigationTools(browser_manager.page)
        result = await nav.navigate("about:blank")
        assert "Navigated" in result


class TestToolRegistration:
    """Test MCP tool registration."""
    
    @pytest.mark.asyncio
    async def test_tools_listed(self):
        """All tools are registered."""
        server = StealthBrowserServer()
        tools = await server.server.list_tools()
        
        tool_names = [t.name for t in tools]
        assert "browser_navigate" in tool_names
        assert "browser_click" in tool_names
        assert "browser_screenshot" in tool_names
```

---

## 6. Implementation Steps

### Step 1: Project Setup
```bash
# Create directory structure
mkdir -p src/browser src/tools tests

# Create Python package files
touch src/__init__.py src/browser/__init__.py src/tools/__init__.py tests/__init__.py

# Create requirements.txt
cat > requirements.txt << 'EOF'
mcp[cli]>=2.0.0
patchright>=0.1.0
pydantic>=2.0.0
anyio>=4.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
EOF

# Install dependencies
pip install -r requirements.txt

# Install browser binaries
patchright install
```

### Step 2: Implement Core Files

Order of implementation:
1. `src/browser/manager.py` - Browser lifecycle
2. `src/tools/navigation.py` - Navigation tools
3. `src/tools/interaction.py` - Interaction tools
4. `src/tools/extraction.py` - Extraction tools
5. `src/server.py` - Main MCP server

### Step 3: Testing
```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Step 4: Manual Testing
```bash
# Start server manually for testing
python -m src.server

# Test with MCP Inspector (if available)
mcp-inspector --server python -m src.server
```

---

## 7. Phase 1 Success Criteria

| Criteria | Status | Notes |
|----------|--------|-------|
| Server starts without errors | ⏳ | Run `python -m src.server` |
| All 7 tools registered | ⏳ | Check tool listing |
| Browser initializes | ⏳ | Check browser manager |
| `browser_navigate` works | ⏳ | Navigate to example.com |
| `browser_click` works | ⏳ | Click on test element |
| `browser_screenshot` works | ⏳ | Capture screenshot |
| Tests pass | ⏳ | `pytest tests/` |
| No lint errors | ⏳ | `ruff check src/` |

---

## 8. Next Phase Dependencies

Phase 1 must complete before Phase 2 can begin:

- **Phase 2** (Stealth): Requires working browser manager
- **Phase 3** (CAPTCHA): Requires Xvfb + PyAutoGUI
- **Phase 4** (Stealth Search): Requires navigation + extraction tools
- **Phase 5** (Data Cleanup): Requires content extraction
- **Phase 6** (Testing): Requires all previous phases
- **Phase 7** (Docker): Requires complete application

---

## 9. Notes & Decisions

### Decisions Made
1. **MCP SDK v2**: Using decorator pattern with `@server.list_tools()` and `@server.call_tool()`
2. **stdio transport**: Phase 1 uses stdio; Phase 7 adds HTTP transport
3. **headless=True**: Phase 1 uses headless; Phase 2 adds Xvfb for stealth
4. **No persistence**: Phase 1 uses ephemeral browser; Phase 2 adds user data dir

### Known Limitations
- No stealth features (detectable as automation)
- No CAPTCHA handling
- No error recovery
- Basic screenshot only (no template matching)
- stdio transport only

### Future Enhancements
- Add tool result caching
- Implement retry logic
- Add request/response logging
- Health check endpoint
