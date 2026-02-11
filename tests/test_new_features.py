"""Unit tests for new Brave Scraper MCP features and validation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.server import BraveScraperServer
from mcp.types import TextContent

@pytest.fixture
def server():
    """Create a server instance with mocked components."""
    with patch('src.server.BrowserManager'):
        server = BraveScraperServer()
        server.browser_manager = MagicMock()
        server.browser_manager.page = AsyncMock()
        server.browser_manager.subagent_manager = None
        return server

@pytest.mark.asyncio
async def test_brave_scrape_page_routing_isolated(server):
    """Verify brave_scrape_page tool calls the correct internal method."""
    with patch('src.server.BraveSearchTools') as MockTools:
        mock_instance = MockTools.return_value
        mock_instance.scrape_page = AsyncMock(return_value="# Markdown Result")
        
        # Mock isolated_context
        mock_page = AsyncMock()
        server.browser_manager.isolated_context.return_value.__aenter__.return_value = mock_page
        
        args = {"url": "https://example.com", "include_images": True}
        result = await server._execute_tool_isolated("brave_scrape_page", args)
        
        mock_instance.scrape_page.assert_called_once_with(
            url="https://example.com", 
            include_images=True
        )
        assert result == "# Markdown Result"

@pytest.mark.asyncio
async def test_brave_scrape_page_routing_shared(server):
    """Verify brave_scrape_page tool calls the correct internal method in shared context."""
    with patch('src.server.BraveSearchTools') as MockTools:
        mock_instance = MockTools.return_value
        mock_instance.scrape_page = AsyncMock(return_value="# Markdown Result")
        
        args = {"url": "https://example.com", "include_images": False}
        result = await server._execute_tool("brave_scrape_page", args)
        
        mock_instance.scrape_page.assert_called_once_with(
            url="https://example.com", 
            include_images=False
        )
        assert result == "# Markdown Result"

@pytest.mark.asyncio
async def test_brave_search_logic_validation():
    """Verify that BraveSearchTools.search raises error for empty query."""
    from src.tools.brave_search import BraveSearchTools
    mock_page = AsyncMock()
    tools = BraveSearchTools(mock_page)
    
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await tools.search(query="")
    
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await tools.search(query="   ")

@pytest.mark.asyncio
async def test_brave_scrape_page_logic():
    """Verify that BraveSearchTools.scrape_page calls markdownify correctly."""
    from src.tools.brave_search import BraveSearchTools
    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html><body><h1>Test</h1></body></html>")
    
    tools = BraveSearchTools(mock_page)
    
    # Patch markdownify.markdownify which was imported as md
    with patch('src.tools.brave_search.md') as mock_md, \
         patch('src.tools.brave_search.MARKDOWNIFY_AVAILABLE', True):
        mock_md.return_value = "# Test"
        res = await tools.scrape_page("https://example.com", include_images=False)
        
        mock_page.goto.assert_called_once()
        # Ensure we called the mock
        assert mock_md.called
        assert res == "# Test"
