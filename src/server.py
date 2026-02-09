#!/usr/bin/env python3
"""
Brave Scraper MCP Server - Phase 1: Core Server
MCP server with basic browser automation tools.
Supports both stdio and streamable-http transports.
"""

import argparse
import asyncio
import logging
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.browser.manager import BrowserManager
from src.browser.captcha import CaptchaSolver
from src.tools.navigation import NavigationTools
from src.tools.interaction import InteractionTools
from src.tools.extraction import ExtractionTools
from src.tools.brave_search import BraveSearchTools, SearchResult, ExtractedContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brave-scraper-mcp")


class BraveScraperServer:
    """MCP Server for Brave Search web scraping with stealth capabilities."""

    def __init__(self):
        self.server = Server("brave-scraper-mcp")
        self.browser_manager: Optional[BrowserManager] = None
        self.nav_tools: Optional[NavigationTools] = None
        self.interact_tools: Optional[InteractionTools] = None
        self.extract_tools: Optional[ExtractionTools] = None
        self.brave_search_tools: Optional[BraveSearchTools] = None

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
                                "description": "When to consider navigation complete",
                            },
                        },
                        "required": ["url"],
                    },
                ),
                Tool(
                    name="browser_back",
                    description="Navigate back in browser history",
                    inputSchema={"type": "object", "properties": {}},
                ),
                # Interaction Tools
                Tool(
                    name="browser_click",
                    description="Click on element matching selector",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for element",
                            }
                        },
                        "required": ["selector"],
                    },
                ),
                Tool(
                    name="browser_fill",
                    description="Fill input field with value",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for input"},
                            "value": {"type": "string", "description": "Value to fill"},
                        },
                        "required": ["selector", "value"],
                    },
                ),
                Tool(
                    name="browser_hover",
                    description="Hover over element matching selector",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for element",
                            }
                        },
                        "required": ["selector"],
                    },
                ),
                # Extraction Tools
                Tool(
                    name="browser_screenshot",
                    description="Capture screenshot of page or element",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Screenshot filename"},
                            "selector": {
                                "type": "string",
                                "description": "Optional: CSS selector for element",
                            },
                            "full_page": {
                                "type": "boolean",
                                "default": False,
                                "description": "Capture full page",
                            },
                        },
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="browser_evaluate",
                    description="Execute JavaScript in browser context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "script": {
                                "type": "string",
                                "description": "JavaScript code to execute",
                            }
                        },
                        "required": ["script"],
                    },
                ),
                # CAPTCHA Solver Tool
                Tool(
                    name="browser_solve_captcha",
                    description="Auto-detect and solve CAPTCHA challenges (Cloudflare Turnstile, hCaptcha, reCAPTCHA)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "timeout": {
                                "type": "integer",
                                "default": 30,
                                "description": "Maximum time to wait for CAPTCHA solving (seconds)",
                            }
                        },
                    },
                ),
                # Brave Search Tools
                Tool(
                    name="brave_search",
                    description="Search Brave Search and return structured results",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query string",
                            },
                            "count": {
                                "type": "integer",
                                "default": 10,
                                "description": "Number of results to return (default: 10)",
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="brave_extract",
                    description="Extract clean, readable content from a URL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to extract content from",
                            },
                            "max_length": {
                                "type": "integer",
                                "default": 5000,
                                "description": "Maximum content length in characters (default: 5000)",
                            },
                        },
                        "required": ["url"],
                    },
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

        elif name == "browser_solve_captcha":
            timeout = arguments.get("timeout", 30)
            captcha_solver = CaptchaSolver()
            result = await captcha_solver.solve(page, timeout=timeout)
            if result.get("success"):
                return f"CAPTCHA solved successfully in {result.get('duration', 0):.2f}s"
            else:
                error_msg = result.get("error", "Unknown error")
                return f"Failed to solve CAPTCHA: {error_msg}"

        # Brave Search tools
        elif name == "brave_search":
            if not self.brave_search_tools:
                self.brave_search_tools = BraveSearchTools(page)

            results = await self.brave_search_tools.search(
                query=arguments["query"], count=arguments.get("count", 10)
            )

            # Format results as readable text
            formatted_results = []
            for result in results:
                formatted_results.append(
                    f"{result.position}. {result.title}\n"
                    f"   URL: {result.url}\n"
                    f"   {result.snippet}\n"
                )

            if not formatted_results:
                return "No results found"

            return f"Found {len(results)} results:\n\n" + "\n".join(formatted_results)

        elif name == "brave_extract":
            if not self.brave_search_tools:
                self.brave_search_tools = BraveSearchTools(page)

            content = await self.brave_search_tools.extract(
                url=arguments["url"], max_length=arguments.get("max_length", 5000)
            )

            # Format extracted content
            result_text = f"Title: {content.title}\n"
            result_text += f"URL: {content.url}\n"
            result_text += f"Word Count: {content.word_count}\n\n"

            if content.summary:
                result_text += f"Summary:\n{content.summary}\n\n"

            result_text += f"Content:\n{content.content}"

            return result_text

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

    async def run_stdio(self):
        """Run the MCP server with stdio transport."""
        await self.initialize()

        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream, write_stream, self.server.create_initialization_options()
                )
        finally:
            await self.cleanup()

    async def run_http(self, port: int = 8080):
        """Run the MCP server with streamable HTTP transport."""
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        from starlette.responses import JSONResponse
        from contextlib import asynccontextmanager

        await self.initialize()

        # Health endpoint
        async def health_check(request):
            """Health check endpoint for Docker/container orchestration."""
            return JSONResponse({"status": "healthy", "server": "brave-scraper-mcp"})

        # Create session manager
        session_manager = StreamableHTTPSessionManager(
            self.server, stateless=True
        )

        @asynccontextmanager
        async def lifespan(app):
            async with session_manager.run():
                yield

        app = Starlette(
            lifespan=lifespan,
            routes=[
                Route("/health", health_check, methods=["GET"]),
                Mount("/mcp", session_manager.handle_request),
            ]
        )

        # Run with uvicorn
        import uvicorn
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)

        try:
            await server.serve()
        finally:
            await self.cleanup()


async def main():
    """Entry point with transport selection."""
    parser = argparse.ArgumentParser(description="Brave Scraper MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport protocol to use",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HTTP transport (default: 8080)",
    )
    args = parser.parse_args()

    server = BraveScraperServer()

    if args.transport == "stdio":
        await server.run_stdio()
    else:
        await server.run_http(port=args.port)


if __name__ == "__main__":
    asyncio.run(main())
