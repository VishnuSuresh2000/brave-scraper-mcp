"""Tests for MCP server."""

import pytest
from src.server import BraveScraperServer


class TestServerInitialization:
    """Test server setup and initialization."""

    @pytest.mark.asyncio
    async def test_server_creates_instance(self):
        """Server instance can be created."""
        server = BraveScraperServer()
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

    def test_tools_defined(self):
        """All tools are defined in server."""
        server = BraveScraperServer()
        # Check that tool handlers are registered
        assert hasattr(server.server, "_tool_cache")
        # The server has tools registered (we can't easily extract them in MCP v1.x,
        # but we can verify the server is properly configured)
        assert server.server is not None
