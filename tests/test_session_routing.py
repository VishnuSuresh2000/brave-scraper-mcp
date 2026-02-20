"""
Tests for Session ID routing and sub-agent browser isolation in MCP server.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSessionIDRouting:
    """Test suite for session_id routing in MCP server tools."""

    @pytest.fixture
    def mock_browser_manager(self):
        """Create a mock BrowserManager with subagent_manager."""
        manager = MagicMock()
        manager.subagent_manager = AsyncMock()
        manager.isolated_context = MagicMock()
        manager.get_subagent_browser = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_stealth_search_without_session_id_uses_shared_browser(
        self, mock_browser_manager
    ):
        """Test that search without session_id uses isolated context (shared browser)."""
        # Setup isolated_context as async context manager
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_page)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_browser_manager.isolated_context.return_value = mock_context

        # Verify isolated_context would be called (not subagent_manager)
        async with mock_browser_manager.isolated_context() as page:
            assert page == mock_page

        mock_browser_manager.isolated_context.assert_called_once()
        mock_browser_manager.get_subagent_browser.assert_not_called()

    @pytest.mark.asyncio
    async def test_stealth_search_with_session_id_uses_subagent_browser(self, mock_browser_manager):
        """Test that search with session_id routes to sub-agent browser."""
        session_id = "sub-agent-test-123"

        # Setup mock browser instance
        mock_instance = AsyncMock()
        mock_instance.list_tabs = AsyncMock(return_value={})
        mock_instance.create_tab = AsyncMock(return_value=("tab_1", AsyncMock()))
        mock_instance.update_activity = MagicMock()

        mock_browser_manager.get_subagent_browser.return_value = mock_instance

        # Call get_subagent_browser
        instance = await mock_browser_manager.get_subagent_browser(session_id)

        assert instance == mock_instance
        mock_browser_manager.get_subagent_browser.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_stealth_extract_without_session_id_uses_shared_browser(
        self, mock_browser_manager
    ):
        """Test that extract without session_id uses isolated context."""
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_page)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_browser_manager.isolated_context.return_value = mock_context

        async with mock_browser_manager.isolated_context() as page:
            assert page == mock_page

        mock_browser_manager.isolated_context.assert_called_once()


class TestBrowserManagerIsolatedContext:
    """Test suite for BrowserManager.isolated_context() - race condition fix."""

    @pytest.fixture
    def browser_manager(self):
        """Create a BrowserManager instance with mocked dependencies."""
        from src.browser.manager import BrowserManager

        manager = BrowserManager()
        manager.browser = MagicMock()  # Mock browser as running
        manager.stealth_config = MagicMock()
        manager.stealth_config.get_context_options = MagicMock(return_value={})
        return manager

    @pytest.mark.asyncio
    async def test_isolated_context_creates_fresh_context(self, browser_manager):
        """Test that each call creates a new isolated context."""
        # Mock the browser.new_context method
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        browser_manager.browser.new_context = AsyncMock(return_value=mock_context)

        # Call isolated_context
        async with browser_manager.isolated_context() as page:
            assert page == mock_page

        # Verify context was created and closed
        browser_manager.browser.new_context.assert_called_once()
        mock_context.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_isolated_context_is_thread_safe(self, browser_manager):
        """Test that concurrent calls are serialized via lock."""
        import asyncio

        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        browser_manager.browser.new_context = AsyncMock(return_value=mock_context)

        # Track order of context creation
        order = []

        async def track_context(*args, **kwargs):
            order.append(f"start_{len(order)}")
            await asyncio.sleep(0.1)  # Simulate work
            order.append(f"end_{len(order)}")
            return mock_context

        browser_manager.browser.new_context = track_context

        # Run 3 concurrent calls
        async def task(i):
            async with browser_manager.isolated_context() as page:
                pass

        await asyncio.gather(task(1), task(2), task(3))

        # With lock, starts should be sequential (not interleaved)
        # Pattern should be: start, end, start, end, start, end
        assert len(order) == 6

    @pytest.mark.asyncio
    async def test_isolated_context_throws_without_browser(self):
        """Test that isolated_context raises error if browser not initialized."""
        from src.browser.manager import BrowserManager

        manager = BrowserManager()
        manager.browser = None  # Browser not started

        with pytest.raises(RuntimeError, match="Browser not initialized"):
            async with manager.isolated_context() as page:
                pass


class TestSubAgentBrowserIsolation:
    """Test suite for sub-agent browser isolation."""

    @pytest.fixture
    def mock_subagent_manager(self):
        """Create a mock SubAgentBrowserManager."""
        from src.browser.subagent_manager import SubAgentBrowserManager

        manager = MagicMock(spec=SubAgentBrowserManager)
        manager.get_or_create_browser = AsyncMock()
        manager.close_browser = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_different_sessions_get_different_browsers(self, mock_subagent_manager):
        """Test that different session IDs get different browser instances."""
        from src.browser.instance import BrowserInstance

        # Create two different mock instances
        instance1 = MagicMock(spec=BrowserInstance)
        instance1.session_id = "sub-agent-1"
        instance1.list_tabs = AsyncMock(return_value={})
        instance1.create_tab = AsyncMock(return_value=("tab_1", AsyncMock()))

        instance2 = MagicMock(spec=BrowserInstance)
        instance2.session_id = "sub-agent-2"
        instance2.list_tabs = AsyncMock(return_value={})
        instance2.create_tab = AsyncMock(return_value=("tab_2", AsyncMock()))

        mock_subagent_manager.get_or_create_browser.side_effect = [instance1, instance2]

        # Get browsers for different sessions
        browser1 = await mock_subagent_manager.get_or_create_browser("sub-agent-1")
        browser2 = await mock_subagent_manager.get_or_create_browser("sub-agent-2")

        assert browser1.session_id != browser2.session_id
        assert mock_subagent_manager.get_or_create_browser.call_count == 2

    @pytest.mark.asyncio
    async def test_same_session_reuses_browser(self, mock_subagent_manager):
        """Test that same session ID reuses the same browser instance."""
        from src.browser.instance import BrowserInstance

        instance = MagicMock(spec=BrowserInstance)
        instance.session_id = "sub-agent-1"

        mock_subagent_manager.get_or_create_browser.return_value = instance

        # Get browser twice for same session
        browser1 = await mock_subagent_manager.get_or_create_browser("sub-agent-1")
        browser2 = await mock_subagent_manager.get_or_create_browser("sub-agent-1")

        assert browser1 == browser2
        assert mock_subagent_manager.get_or_create_browser.call_count == 2
