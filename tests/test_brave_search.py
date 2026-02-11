import pytest
from unittest.mock import AsyncMock, MagicMock

from src.tools.brave_search import BraveSearchTools, SearchResult, SearchResponse, brave_search

class TestValidationErrors:
    """Test suite for input validation in BraveSearchTools."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.evaluate = AsyncMock()
        return page

    @pytest.fixture
    def search_tools(self, mock_page):
        """Create a BraveSearchTools instance."""
        return BraveSearchTools(mock_page)

    @pytest.mark.asyncio
    async def test_search_empty_query_raises_error(self, search_tools, mock_page):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await search_tools.search("")

    @pytest.mark.asyncio
    async def test_search_whitespace_query_raises_error(self, search_tools, mock_page):
        """Test that whitespace-only query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await search_tools.search("   ")

    @pytest.mark.asyncio
    async def test_search_none_query_raises_error(self, search_tools, mock_page):
        """Test that None query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await search_tools.search(None)  # type: ignore

    @pytest.mark.asyncio
    async def test_search_page_zero_raises_error(self, search_tools, mock_page):
        """Test that page=0 raises ValueError."""
        with pytest.raises(ValueError, match="Page must be between 1 and 100"):
            await search_tools.search("test", page=0)

    @pytest.mark.asyncio
    async def test_search_page_negative_raises_error(self, search_tools, mock_page):
        """Test that negative page raises ValueError."""
        with pytest.raises(ValueError, match="Page must be between 1 and 100"):
            await search_tools.search("test", page=-1)

    @pytest.mark.asyncio
    async def test_search_page_exceeds_max_raises_error(self, search_tools, mock_page):
        """Test that page > 100 raises ValueError."""
        with pytest.raises(ValueError, match="Page must be between 1 and 100"):
            await search_tools.search("test", page=101)

    @pytest.mark.asyncio
    async def test_search_count_zero_raises_error(self, search_tools, mock_page):
        """Test that count=0 raises ValueError."""
        with pytest.raises(ValueError, match="Count must be between 1 and 100"):
            await search_tools.search("test", count=0)

    @pytest.mark.asyncio
    async def test_search_count_negative_raises_error(self, search_tools, mock_page):
        """Test that negative count raises ValueError."""
        with pytest.raises(ValueError, match="Count must be between 1 and 100"):
            await search_tools.search("test", count=-5)

    @pytest.mark.asyncio
    async def test_search_count_exceeds_max_raises_error(self, search_tools, mock_page):
        """Test that count > 100 raises ValueError."""
        with pytest.raises(ValueError, match="Count must be between 1 and 100"):
            await search_tools.search("test", count=101)

    @pytest.mark.asyncio
    async def test_search_max_page_boundary(self, search_tools, mock_page):
        """Test that page=100 is valid."""
        mock_page.evaluate = AsyncMock(return_value={"results": [], "aiSummary": None})
        response = await search_tools.search("test", page=100)
        assert response.page == 100

    @pytest.mark.asyncio
    async def test_search_max_count_boundary(self, search_tools, mock_page):
        """Test that count=100 is valid."""
        mock_page.evaluate = AsyncMock(return_value={"results": [], "aiSummary": None})
        response = await search_tools.search("test", count=100)
        assert response.results == []


class TestValidationConstants:
    """Test suite for validation constants."""

    def test_max_page_constant_exists(self):
        """Test that MAX_PAGE constant exists and is correct."""
        assert BraveSearchTools.MAX_PAGE == 100

    def test_max_count_constant_exists(self):
        """Test that MAX_COUNT constant exists and is correct."""
        assert BraveSearchTools.MAX_COUNT == 100


class TestServerValidation:
    """Test suite for server-side selector validation."""

    @pytest.mark.asyncio
    async def test_browser_click_empty_selector_raises_error(self):
        """Test that empty selector raises ValueError in browser_click."""
        from src.server import BraveScraperServer

        server_instance = BraveScraperServer.__new__(BraveScraperServer)
        server_instance.browser_manager = MagicMock()
        server_instance.browser_manager.page = AsyncMock()
        
        with pytest.raises(ValueError, match="Selector cannot be empty"):
            await server_instance._execute_tool("browser_click", {"selector": ""})

    @pytest.mark.asyncio
    async def test_browser_click_whitespace_selector_raises_error(self):
        """Test that whitespace-only selector raises ValueError."""
        from src.server import BraveScraperServer

        server_instance = BraveScraperServer.__new__(BraveScraperServer)
        server_instance.browser_manager = MagicMock()
        server_instance.browser_manager.page = AsyncMock()
        
        with pytest.raises(ValueError, match="Selector cannot be empty"):
            await server_instance._execute_tool("browser_click", {"selector": "   "})

    @pytest.mark.asyncio
    async def test_browser_fill_empty_selector_raises_error(self):
        """Test that empty selector raises ValueError in browser_fill."""
        from src.server import BraveScraperServer

        server_instance = BraveScraperServer.__new__(BraveScraperServer)
        server_instance.browser_manager = MagicMock()
        server_instance.browser_manager.page = AsyncMock()
        
        with pytest.raises(ValueError, match="Selector cannot be empty"):
            await server_instance._execute_tool("browser_fill", {"selector": "", "value": "test"})

    @pytest.mark.asyncio
    async def test_browser_hover_empty_selector_raises_error(self):
        """Test that empty selector raises ValueError in browser_hover."""
        from src.server import BraveScraperServer

        server_instance = BraveScraperServer.__new__(BraveScraperServer)
        server_instance.browser_manager = MagicMock()
        server_instance.browser_manager.page = AsyncMock()
        
        with pytest.raises(ValueError, match="Selector cannot be empty"):
            await server_instance._execute_tool("browser_hover", {"selector": ""})
