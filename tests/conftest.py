"""pytest fixtures."""

import os
import sys
from unittest.mock import MagicMock

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


@pytest_asyncio.fixture
async def browser_manager():
    """Browser manager fixture."""
    manager = BrowserManager()
    await manager.start()
    yield manager
    await manager.stop()
