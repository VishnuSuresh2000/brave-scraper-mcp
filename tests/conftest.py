"""pytest fixtures."""

import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Set DISPLAY environment variable before importing pyautogui
os.environ.setdefault("DISPLAY", ":99")

# Mock pyautogui BEFORE any imports to avoid X11 connection issues
_mock_pyautogui = MagicMock()
_mock_pyautogui.position.return_value = (0, 0)
_mock_pyautogui.size.return_value = (1920, 1080)
sys.modules["pyautogui"] = _mock_pyautogui

import pytest
import pytest_asyncio

from src.browser.manager import BrowserManager


def is_ci():
    """Check if running in CI environment."""
    return os.environ.get("CI", "").lower() in ("true", "1")


@pytest_asyncio.fixture
async def browser_manager():
    """Browser manager fixture.
    
    In CI: Uses mock to avoid hanging on real browser launch.
    Locally: Uses real browser for integration testing.
    """
    if is_ci():
        # Use mock in CI to avoid hanging
        manager = MagicMock(spec=BrowserManager)
        manager.context = AsyncMock()
        manager.page = AsyncMock()
        manager.page.goto = AsyncMock(return_value=None)
        manager.page.go_back = AsyncMock(return_value=None)
        manager.page.click = AsyncMock(return_value=None)
        manager.page.fill = AsyncMock(return_value=None)
        manager.page.hover = AsyncMock(return_value=None)
        manager.page.evaluate = AsyncMock(return_value="result")
        manager.page.screenshot = AsyncMock(return_value=b"fake_image")
        manager.page.query_selector = AsyncMock(return_value=None)
        manager.stop = AsyncMock()
        yield manager
    else:
        # Real browser for local testing
        manager = BrowserManager()
        await manager.start()
        yield manager
        await manager.stop()
