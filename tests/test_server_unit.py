"""Unit tests for StealthBrowserServer tool routing and logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.server import StealthBrowserServer
from mcp.types import TextContent


@pytest.fixture
def server():
    """Create a server instance with mocked components."""
    with patch("src.server.BrowserManager"):
        server = StealthBrowserServer()
        server.browser_manager = MagicMock()
        server.browser_manager.page = AsyncMock()
        return server


@pytest.mark.asyncio
async def test_execute_tool_browser_navigate(server):
    """Test browser_navigate routing."""
    result = await server._execute_tool("browser_navigate", {"url": "https://example.com"})
    server.browser_manager.page.goto.assert_called_once_with(
        "https://example.com", wait_until="load"
    )
    assert "Navigated to https://example.com" in result


@pytest.mark.asyncio
async def test_execute_tool_browser_back(server):
    """Test browser_back routing."""
    result = await server._execute_tool("browser_back", {})
    server.browser_manager.page.go_back.assert_called_once()
    assert "Navigated back" in result


@pytest.mark.asyncio
async def test_execute_tool_browser_click(server):
    """Test browser_click routing."""
    result = await server._execute_tool("browser_click", {"selector": "button"})
    server.browser_manager.page.click.assert_called_once_with("button")
    assert "Clicked element: button" in result


@pytest.mark.asyncio
async def test_execute_tool_browser_fill(server):
    """Test browser_fill routing."""
    result = await server._execute_tool("browser_fill", {"selector": "input", "value": "test"})
    server.browser_manager.page.fill.assert_called_once_with("input", "test")
    assert "Filled input with value" in result


@pytest.mark.asyncio
async def test_execute_tool_browser_hover(server):
    """Test browser_hover routing."""
    result = await server._execute_tool("browser_hover", {"selector": "div"})
    server.browser_manager.page.hover.assert_called_once_with("div")
    assert "Hovered over div" in result


@pytest.mark.asyncio
async def test_execute_tool_browser_evaluate(server):
    """Test browser_evaluate routing."""
    server.browser_manager.page.evaluate.return_value = "evaluated"
    result = await server._execute_tool("browser_evaluate", {"script": "1+1"})
    server.browser_manager.page.evaluate.assert_called_once_with("1+1")
    assert result == "evaluated"


@pytest.mark.asyncio
async def test_execute_tool_browser_screenshot(server):
    """Test browser_screenshot routing."""
    # Full page
    result = await server._execute_tool("browser_screenshot", {"name": "test", "full_page": True})
    server.browser_manager.page.screenshot.assert_called_with(path="/tmp/test.png", full_page=True)
    assert "Screenshot saved" in result

    # Selector based
    mock_element = AsyncMock()
    server.browser_manager.page.query_selector.return_value = mock_element
    result = await server._execute_tool("browser_screenshot", {"name": "elem", "selector": ".box"})
    server.browser_manager.page.query_selector.assert_called_with(".box")
    mock_element.screenshot.assert_called_once_with(path="/tmp/elem.png")
    assert "Screenshot saved" in result


@pytest.mark.asyncio
async def test_execute_tool_stealth_search(server):
    """Test stealth_search routing."""
    with patch("src.server.StealthSearchTools") as MockTools:
        mock_instance = MockTools.return_value
        mock_instance.search = AsyncMock(
            return_value=MagicMock(
                query="test",
                results=[MagicMock(title="T1", url="U1", snippet="S1", position=1)],
                ai_summary=None,
            )
        )

        # Mock isolated_context to return a mock page
        mock_page = AsyncMock()
        server.browser_manager.isolated_context.return_value.__aenter__.return_value = mock_page

        result = await server._execute_tool_isolated(
            "stealth_search", {"query": "test", "count": 1}
        )
        mock_instance.search.assert_called_once_with(query="test", count=1, page=1)
        assert "1. T1" in result
        assert "URL: U1" in result


@pytest.mark.asyncio
async def test_execute_tool_stealth_extract(server):
    """Test stealth_extract routing."""
    with patch("src.server.StealthSearchTools") as MockTools:
        mock_instance = MockTools.return_value
        mock_instance.extract = AsyncMock(
            return_value=MagicMock(
                title="Title", url="Url", content="Content", word_count=10, summary="Summary"
            )
        )

        # Mock isolated_context to return a mock page
        mock_page = AsyncMock()
        server.browser_manager.isolated_context.return_value.__aenter__.return_value = mock_page

        result = await server._execute_tool_isolated("stealth_extract", {"url": "https://test.com"})
        mock_instance.extract.assert_called_once_with(url="https://test.com", max_length=5000)
        assert "Title: Title" in result
        assert "Summary:\nSummary" in result
        assert "Content:\nContent" in result


@pytest.mark.asyncio
async def test_execute_tool_captcha(server):
    """Test browser_solve_captcha routing."""
    with patch("src.server.CaptchaSolver") as MockSolver:
        mock_instance = MockSolver.return_value
        mock_instance.solve = AsyncMock(return_value={"success": True, "duration": 1.5})

        result = await server._execute_tool("browser_solve_captcha", {"timeout": 10})
        mock_instance.solve.assert_called_once()
        assert "solved successfully in 1.50s" in result


@pytest.mark.asyncio
async def test_execute_tool_unknown(server):
    """Test unknown tool handling."""
    result = await server._execute_tool("unknown_tool", {})
    assert "Unknown tool: unknown_tool" in result


@pytest.mark.asyncio
async def test_call_tool_handler(server):
    """Test the main call_tool handler including error handling."""
    # Test uninitialized browser
    server.browser_manager.page = None
    resp = await server.call_tool_handler("browser_navigate", {"url": "..."})
    assert "Error: Browser page not available" in resp[0].text

    # Test success
    server.browser_manager.page = AsyncMock()
    with patch.object(server, "_execute_tool", AsyncMock(return_value="OK")):
        resp = await server.call_tool_handler("browser_navigate", {"url": "..."})
        assert resp[0].text == "OK"

    # Test exception
    with patch.object(server, "_execute_tool", AsyncMock(side_effect=Exception("Failed"))):
        resp = await server.call_tool_handler("browser_navigate", {"url": "..."})
        assert "Error: Failed" in resp[0].text
