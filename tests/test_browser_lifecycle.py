import asyncio
import os
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.browser.instance import BrowserInstance, TabInfo
from src.browser.subagent_manager import SubAgentBrowserManager

# Skip browser lifecycle tests in CI - they need real browser
CI_SKIP = os.environ.get("CI", "").lower() == "true"

@pytest.mark.asyncio
class TestBrowserInstance:
    """Tests for BrowserInstance class."""

    async def test_instance_creation(self):
        """Test BrowserInstance initialization."""
        mock_browser = MagicMock()
        mock_context = AsyncMock()
        instance = BrowserInstance("test-session", mock_browser, mock_context)
        
        assert instance.session_id == "test-session"
        assert instance.tab_count == 0
        assert instance.is_active is True
        assert instance._closed is False

    async def test_create_tab(self):
        """Test tab creation and tracking."""
        mock_browser = MagicMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        instance = BrowserInstance("test-session", mock_browser, mock_context)
        tab_id, page = await instance.create_tab(url="https://example.com")
        
        assert tab_id.startswith("tab_")
        assert page == mock_page
        assert instance.tab_count == 1
        assert "https://example.com" in (await instance.list_tabs())[tab_id]["url"]
        mock_page.goto.assert_called_once_with("https://example.com", wait_until="domcontentloaded")

    async def test_tab_limit_eviction(self):
        """Test that oldest tabs are evicted when limit is reached."""
        mock_browser = MagicMock()
        mock_context = AsyncMock()
        mock_pages = [AsyncMock() for _ in range(20)]
        mock_context.new_page.side_effect = mock_pages
        
        instance = BrowserInstance("test-session", mock_browser, mock_context)
        instance.MAX_TABS = 3
        
        # Create 3 tabs
        id1, _ = await instance.create_tab(tab_id="tab1")
        id2, _ = await instance.create_tab(tab_id="tab2")
        id3, _ = await instance.create_tab(tab_id="tab3")
        
        assert instance.tab_count == 3
        
        # Create 4th tab - should evict tab1
        id4, _ = await instance.create_tab(tab_id="tab4")
        
        assert instance.tab_count == 3
        tabs = await instance.list_tabs()
        assert "tab1" not in tabs
        assert "tab4" in tabs
        mock_pages[0].close.assert_called_once()

    async def test_lru_behavior(self):
        """Test that get_tab updates LRU order."""
        mock_browser = MagicMock()
        mock_context = AsyncMock()
        mock_context.new_page.return_value = AsyncMock()
        
        instance = BrowserInstance("test-session", mock_browser, mock_context)
        instance.MAX_TABS = 2
        
        id1, _ = await instance.create_tab(tab_id="tab1")
        id2, _ = await instance.create_tab(tab_id="tab2")
        
        # Access tab1 to make it "recent"
        await instance.get_tab(id1)
        
        # Create tab3 - should evict tab2 (because tab1 was accessed)
        id3, _ = await instance.create_tab(tab_id="tab3")
        
        tabs = await instance.list_tabs()
        assert "tab2" not in tabs
        assert "tab1" in tabs
        assert "tab3" in tabs

@pytest.mark.asyncio
@pytest.mark.skipif(CI_SKIP, reason="Browser lifecycle tests require real browser - skipped in CI")
class TestSubAgentBrowserManager:
    """Tests for SubAgentBrowserManager class."""

    @pytest.fixture
    async def manager(self):
        with patch('src.browser.subagent_manager.async_playwright') as mock_pw:
            # Create a mock for the object returned by async_playwright()
            mock_cm = MagicMock()
            mock_pw.return_value = mock_cm
            
            # Create a mock for the Playwright object returned by .start()
            mock_pw_instance = AsyncMock()
            
            # Make .start() return the playwright instance
            mock_cm.start = AsyncMock(return_value=mock_pw_instance)
            
            # Setup chromium mock
            mock_pw_instance.chromium = MagicMock()
            mock_pw_instance.chromium.launch = AsyncMock()
            
            manager = SubAgentBrowserManager(idle_timeout_minutes=1)
            await manager.start()
            yield manager
            await manager.stop()

    async def test_manager_start_stop(self, manager):
        """Test manager lifecycle."""
        assert manager._running is True
        assert manager._playwright is not None
        assert manager._cleanup_task is not None
        
        await manager.stop()
        assert manager._running is False
        assert manager._playwright is None
        assert manager._cleanup_task is None

    async def test_create_browser(self, manager):
        """Test browser instance creation for sub-agent."""
        mock_browser = AsyncMock()
        manager._playwright.chromium.launch.return_value = mock_browser
        
        instance = await manager.create_browser("sub-1")
        
        assert instance.session_id == "sub-1"
        assert "sub-1" in manager._browsers
        assert manager._browser_refs["sub-1"] == mock_browser
        mock_browser.new_context.assert_called_once()

    async def test_cleanup_inactive(self, manager):
        """Test automatic cleanup of idle browsers."""
        mock_browser = AsyncMock()
        manager._playwright.chromium.launch.return_value = mock_browser
        
        # Set short timeout for test
        manager.IDLE_TIMEOUT_SECONDS = 0.1
        
        instance = await manager.create_browser("sub-idle")
        assert "sub-idle" in manager._browsers
        
        # Wait for timeout
        await asyncio.sleep(0.2)
        
        # Run cleanup
        await manager._cleanup_inactive()
        
        assert "sub-idle" not in manager._browsers
        mock_browser.close.assert_called()
