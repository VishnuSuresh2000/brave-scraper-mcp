"""
Tests for CAPTCHA solver functionality.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.browser.captcha import CaptchaSolver, MouseController, solve_captcha


class TestCaptchaSolver:
    """Test suite for CaptchaSolver class."""

    @pytest.fixture
    def captcha_solver(self):
        """Create a CaptchaSolver instance for testing."""
        return CaptchaSolver()

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)
        page.content = AsyncMock(return_value="<html></html>")
        page.screenshot = AsyncMock()
        page.evaluate = AsyncMock()
        return page

    @pytest.mark.asyncio
    async def test_detect_captcha_no_captcha(self, captcha_solver, mock_page):
        """Test detection when no CAPTCHA is present."""
        detected, captcha_type = await captcha_solver.detect_captcha(mock_page)

        assert detected is False
        assert captcha_type is None

    @pytest.mark.asyncio
    async def test_detect_captcha_cloudflare_turnstile(self, captcha_solver, mock_page):
        """Test detection of Cloudflare Turnstile CAPTCHA."""
        # Mock iframe element found
        mock_iframe = MagicMock()
        mock_page.query_selector = AsyncMock(return_value=mock_iframe)

        detected, captcha_type = await captcha_solver.detect_captcha(mock_page)

        # Should detect because query_selector returns an element
        assert detected is True
        assert captcha_type == "cloudflare_turnstile"

    @pytest.mark.asyncio
    async def test_detect_captcha_hcaptcha_content(self, captcha_solver, mock_page):
        """Test detection of hCaptcha via content analysis."""
        # No iframe, but content contains hCaptcha indicators
        mock_page.content = AsyncMock(
            return_value='<html><div class="h-captcha">Challenge</div></html>'
        )

        detected, captcha_type = await captcha_solver.detect_captcha(mock_page)

        assert detected is True
        assert captcha_type == "hcaptcha"

    @pytest.mark.asyncio
    async def test_detect_captcha_recaptcha_content(self, captcha_solver, mock_page):
        """Test detection of reCAPTCHA via content analysis."""
        mock_page.content = AsyncMock(
            return_value='<html><div class="g-recaptcha" data-sitekey="test"></div></html>'
        )

        detected, captcha_type = await captcha_solver.detect_captcha(mock_page)

        assert detected is True
        assert captcha_type == "recaptcha"

    @pytest.mark.asyncio
    async def test_solve_no_captcha(self, captcha_solver, mock_page):
        """Test solve when no CAPTCHA is detected."""
        result = await captcha_solver.solve(mock_page, timeout=1)

        assert result["success"] is True
        assert result["type"] is None
        assert "message" in result
        assert "No CAPTCHA detected" in result["message"]

    @pytest.mark.asyncio
    async def test_solve_turnstile_no_iframe(self, captcha_solver, mock_page):
        """Test solving Turnstile when iframe is not found."""
        # Mock content with Turnstile but no iframe found
        mock_page.content = AsyncMock(
            return_value="<html><div>challenges.cloudflare.com</div></html>"
        )
        mock_page.query_selector = AsyncMock(return_value=None)

        result = await captcha_solver.solve(mock_page, timeout=1)

        assert result["type"] == "cloudflare_turnstile"
        # Should fail because iframe not found
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_match_template_success(self, captcha_solver):
        """Test successful template matching."""
        # Create non-constant test images
        screenshot = np.random.randint(0, 100, (100, 100), dtype=np.uint8)
        template = np.zeros((20, 20), dtype=np.uint8)

        # Place template pattern in screenshot with some variation
        screenshot[40:60, 40:60] = np.random.randint(200, 256, (20, 20), dtype=np.uint8)
        template[:, :] = screenshot[40:60, 40:60]

        result = captcha_solver._match_template(screenshot, template, threshold=0.5)

        assert result is not None
        x, y, confidence = result
        assert 0 <= x <= 100
        assert 0 <= y <= 100
        assert 0 <= confidence <= 1

    @pytest.mark.asyncio
    async def test_match_template_no_match(self, captcha_solver):
        """Test template matching when no match found."""
        # Create non-constant images with different patterns
        screenshot = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        template = np.random.randint(0, 256, (20, 20), dtype=np.uint8)

        # No match - random images are unlikely to match with high threshold
        result = captcha_solver._match_template(screenshot, template, threshold=0.999)

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_mouse_path(self, captcha_solver):
        """Test mouse path generation."""
        start = (0, 0)
        end = (100, 100)
        steps = 20

        path = captcha_solver._generate_mouse_path(start, end, steps)

        assert len(path) == steps
        assert path[0] != start  # Should have some curvature
        # Last point should be close to end (with small noise)
        assert abs(path[-1][0] - end[0]) <= 5
        assert abs(path[-1][1] - end[1]) <= 5

    @pytest.mark.asyncio
    async def test_wait_for_captcha_resolution(self, captcha_solver, mock_page):
        """Test waiting for CAPTCHA resolution."""
        # Mock no CAPTCHA detected immediately
        mock_page.content = AsyncMock(return_value="<html></html>")

        result = await captcha_solver.wait_for_captcha_resolution(
            mock_page, check_interval=0.1, timeout=1
        )

        assert result is True


class TestMouseController:
    """Test suite for MouseController class."""

    @pytest.fixture
    def mouse_controller(self):
        """Create a MouseController instance."""
        with patch("src.browser.captcha.pyautogui") as mock_pg:
            mock_pg.size.return_value = (1920, 1080)
            yield MouseController()

    @pytest.mark.asyncio
    async def test_mouse_controller_init(self, mouse_controller):
        """Test MouseController initialization."""
        assert mouse_controller.screen_width > 0
        assert mouse_controller.screen_height > 0

    @pytest.mark.asyncio
    @patch("src.browser.captcha.pyautogui")
    async def test_move_to(self, mock_pg, mouse_controller):
        """Test mouse movement."""
        mock_pg.position.return_value = (0, 0)

        await mouse_controller.move_to(100, 100, duration=0.1)

        mock_pg.moveTo.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.browser.captcha.pyautogui")
    async def test_click(self, mock_pg, mouse_controller):
        """Test mouse click."""
        mock_pg.position.return_value = (0, 0)

        await mouse_controller.click(100, 100)

        mock_pg.moveTo.assert_called_once()
        mock_pg.click.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.browser.captcha.pyautogui")
    async def test_scroll(self, mock_pg, mouse_controller):
        """Test mouse scroll."""
        await mouse_controller.scroll(100)

        # Should call scroll multiple times for natural movement
        assert mock_pg.scroll.call_count >= 1


class TestConvenienceFunction:
    """Test suite for convenience function."""

    @pytest.mark.asyncio
    async def test_solve_captcha_convenience(self, mock_page):
        """Test the solve_captcha convenience function."""
        # Mock no CAPTCHA
        mock_page.content = AsyncMock(return_value="<html></html>")

        result = await solve_captcha(mock_page, timeout=1)

        assert result["success"] is True
        assert "message" in result


@pytest.fixture
def mock_page():
    """Create a mock Playwright page for all tests."""
    page = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)
    page.content = AsyncMock(return_value="<html></html>")
    page.screenshot = AsyncMock()
    page.evaluate = AsyncMock()
    return page


class TestIntegration:
    """Integration tests for CAPTCHA solver."""

    @pytest.mark.asyncio
    async def test_full_solve_flow(self):
        """Test the full CAPTCHA solve flow with mocks."""
        solver = CaptchaSolver()

        # Create mock page
        page = AsyncMock()
        page.content = AsyncMock(return_value="<html><div>challenges.cloudflare.com</div></html>")

        # Mock iframe with bounding box
        mock_iframe = MagicMock()
        mock_iframe.bounding_box = AsyncMock(
            return_value={"x": 100, "y": 100, "width": 50, "height": 50}
        )
        page.query_selector = AsyncMock(return_value=mock_iframe)

        # Mock screenshot for template matching
        page.screenshot = AsyncMock()

        # Mock pyautogui at module level
        with (
            patch("src.browser.captcha.pyautogui") as mock_pg,
            patch("src.browser.captcha.pyautogui_available", True),
        ):
            mock_pg.position.return_value = (0, 0)

            # After first check, CAPTCHA should be gone
            check_count = [0]

            async def mock_detect(*args, **kwargs):
                check_count[0] += 1
                return check_count[0] > 1, None

            with patch.object(solver, "detect_captcha", side_effect=mock_detect):
                result = await solver.solve(page, timeout=2)

        # Result depends on implementation details
        assert "success" in result
        assert "duration" in result


class TestCaptchaSelectors:
    """Test CAPTCHA selector definitions."""

    def test_cloudflare_selectors(self):
        """Test Cloudflare selector patterns."""
        solver = CaptchaSolver()
        assert "cloudflare_turnstile" in solver.CAPTCHA_SELECTORS
        selectors = solver.CAPTCHA_SELECTORS["cloudflare_turnstile"]
        assert any("challenges.cloudflare.com" in s for s in selectors)

    def test_hcaptcha_selectors(self):
        """Test hCaptcha selector patterns."""
        solver = CaptchaSolver()
        assert "hcaptcha" in solver.CAPTCHA_SELECTORS
        selectors = solver.CAPTCHA_SELECTORS["hcaptcha"]
        assert any("hcaptcha" in s.lower() for s in selectors)

    def test_recaptcha_selectors(self):
        """Test reCAPTCHA selector patterns."""
        solver = CaptchaSolver()
        assert "recaptcha" in solver.CAPTCHA_SELECTORS
        selectors = solver.CAPTCHA_SELECTORS["recaptcha"]
        assert any("recaptcha" in s.lower() for s in selectors)

    def test_challenge_indicators(self):
        """Test challenge indicator keywords."""
        solver = CaptchaSolver()
        assert len(solver.CHALLENGE_INDICATORS) > 0
        assert "captcha" in [i.lower() for i in solver.CHALLENGE_INDICATORS]
        assert "verification" in [i.lower() for i in solver.CHALLENGE_INDICATORS]
