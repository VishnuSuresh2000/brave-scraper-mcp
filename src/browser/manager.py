"""
Browser lifecycle management using Patchright.
Phase 2: Stealth browser with Xvfb and anti-detection.
"""

import os
import logging
from typing import Optional

from patchright.async_api import async_playwright, Browser, BrowserContext, Page

from src.browser.stealth import StealthConfig, XvfbManager, detect_display, setup_xvfb_env

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser lifecycle with stealth capabilities."""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Stealth configuration
        self.stealth_config = StealthConfig()
        self.xvfb_manager: Optional[XvfbManager] = None

        # Setup display environment
        self.display = setup_xvfb_env()

    async def start(self):
        """Start browser instance with stealth configuration."""
        logger.info("Starting browser with stealth configuration...")
        logger.info(f"Stealth mode: {self.stealth_config.stealth_mode}")
        logger.info(f"Display: {self.display}")

        # Start Xvfb if needed for stealth mode
        if self.stealth_config.use_xvfb:
            await self._start_xvfb()

        self.playwright = await async_playwright().start()

        # Determine launch method based on configuration
        if self.stealth_config.stealth_mode:
            await self._launch_stealth_browser()
        else:
            await self._launch_basic_browser()

        logger.info("Browser started successfully")

    async def _start_xvfb(self):
        """Start Xvfb virtual display if needed."""
        self.xvfb_manager = XvfbManager(display=self.display)
        success = await self.xvfb_manager.start()

        if not success:
            logger.warning(
                "Failed to start Xvfb. Falling back to headless mode. "
                "Some stealth features may not work."
            )
            # Fall back to headless if Xvfb fails
            self.stealth_config.headless = True

    async def _launch_stealth_browser(self):
        """Launch browser with maximum stealth configuration."""
        logger.info("Launching browser in stealth mode...")

        launch_args = self.stealth_config.get_launch_args()
        context_options = self.stealth_config.get_context_options()

        try:
            # Attempt to use persistent context with Chrome channel for maximum stealth
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.stealth_config.user_data_dir,
                channel=self.stealth_config.channel,  # Use real Chrome if available
                headless=self.stealth_config.headless,
                args=launch_args,
                no_viewport=True,  # Let browser use natural viewport
                **{k: v for k, v in context_options.items() if k != "viewport"},
            )

            # Get the default page from persistent context
            pages = self.context.pages
            if pages:
                self.page = pages[0]
            else:
                self.page = await self.context.new_page()

            logger.info(f"Using channel: {self.stealth_config.channel}")
            logger.info(f"Headless: {self.stealth_config.headless}")

        except Exception as e:
            logger.warning(f"Failed to launch with Chrome channel: {e}")
            logger.info("Falling back to standard Chromium...")

            # Fallback to regular Chromium
            await self._launch_basic_browser()

    async def _launch_basic_browser(self):
        """Launch basic browser without stealth optimizations."""
        logger.info("Launching basic browser...")

        self.browser = await self.playwright.chromium.launch(
            headless=self.stealth_config.headless,
            args=self.stealth_config.get_launch_args(),
        )

        context_options = self.stealth_config.get_context_options()
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()

    async def stop(self):
        """Stop browser and cleanup resources."""
        logger.info("Stopping browser...")

        if self.page:
            try:
                await self.page.close()
            except Exception as e:
                logger.debug(f"Error closing page: {e}")
            self.page = None

        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                logger.debug(f"Error closing context: {e}")
            self.context = None

        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")
            self.browser = None

        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.debug(f"Error stopping playwright: {e}")
            self.playwright = None

        # Stop Xvfb if we started it
        if self.xvfb_manager:
            await self.xvfb_manager.stop()
            self.xvfb_manager = None

        logger.info("Browser stopped")

    async def new_page(self) -> Page:
        """Create a new page in the context."""
        if not self.context:
            raise RuntimeError("Browser not initialized")
        return await self.context.new_page()

    async def check_stealth(self) -> dict:
        """Check stealth status and browser fingerprint.

        Returns:
            Dictionary with stealth detection information.
        """
        if not self.page:
            return {"error": "Browser not initialized"}

        # JavaScript to check for automation indicators
        stealth_check_script = """
        () => {
            return {
                webdriver: navigator.webdriver,
                plugins: navigator.plugins.length,
                languages: navigator.languages,
                platform: navigator.platform,
                userAgent: navigator.userAgent,
                vendor: navigator.vendor,
                deviceMemory: navigator.deviceMemory,
                hardwareConcurrency: navigator.hardwareConcurrency,
                maxTouchPoints: navigator.maxTouchPoints,
                chrome: typeof window.chrome !== 'undefined',
                notificationPermission: Notification.permission,
                // Check for common automation indicators
                automationControlled: navigator.webdriver === true,
                hasPlugins: navigator.plugins.length > 0,
                hasMimeTypes: navigator.mimeTypes.length > 0,
            };
        }
        """

        try:
            result = await self.page.evaluate(stealth_check_script)
            result["stealth_mode"] = self.stealth_config.stealth_mode
            result["display"] = self.display
            result["channel"] = self.stealth_config.channel
            return result
        except Exception as e:
            return {"error": str(e)}
