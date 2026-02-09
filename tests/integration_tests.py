#!/usr/bin/env python3
"""
Phase 6: Real-world integration tests
Tests stealth, Brave Search, and content extraction
"""

import asyncio
import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, "/home/node/.openclaw/workspace/brave-scraper-mcp")

from src.browser.manager import BrowserManager
from src.tools.brave_search import BraveSearchTools


async def test_stealth():
    """Test stealth against bot.sannysoft.com"""
    logger.info("=" * 60)
    logger.info("TEST 1: Stealth Test against bot.sannysoft.com")
    logger.info("=" * 60)

    results = {
        "test": "Stealth Detection",
        "url": "https://bot.sannysoft.com",
        "status": "PENDING",
        "details": {},
    }

    browser = None
    try:
        browser = BrowserManager()
        await browser.start()

        # Navigate to sannysoft
        logger.info("Navigating to bot.sannysoft.com...")
        await browser.page.goto("https://bot.sannysoft.com", wait_until="networkidle")
        await browser.page.wait_for_timeout(3000)

        # Run stealth check
        stealth_info = await browser.check_stealth()
        results["details"]["browser_fingerprint"] = stealth_info

        # Check for common detection indicators on the page
        detection_results = await browser.page.evaluate("""
            () => {
                const results = {};
                
                // Check for red warnings (indicating detection)
                const redElements = document.querySelectorAll('*');
                let redFlags = [];
                redElements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.color === 'rgb(255, 0, 0)' || style.backgroundColor === 'rgb(255, 0, 0)') {
                        const text = el.textContent?.trim();
                        if (text && text.length > 0 && text.length < 200) {
                            redFlags.push(text);
                        }
                    }
                });
                results.redFlags = [...new Set(redFlags)].slice(0, 10);
                
                // Check WebDriver detection
                results.webdriverDetected = navigator.webdriver === true;
                
                // Check plugins
                results.pluginsCount = navigator.plugins?.length || 0;
                
                // Check for automation properties
                results.hasChrome = typeof window.chrome !== 'undefined';
                results.hasPermissions = typeof navigator.permissions !== 'undefined';
                
                return results;
            }
        """)

        results["details"]["page_detection"] = detection_results

        # Determine pass/fail
        issues = []
        if detection_results.get("webdriverDetected"):
            issues.append("navigator.webdriver is true")
        if detection_results.get("pluginsCount", 0) < 2:
            issues.append(f"Only {detection_results.get('pluginsCount', 0)} plugins detected")

        if issues:
            results["status"] = "WARNING"
            results["issues"] = issues
            logger.warning(f"Stealth issues detected: {issues}")
        else:
            results["status"] = "PASS"
            logger.info("Stealth test PASSED - no obvious detection indicators")

        # Take screenshot
        screenshot_path = "/tmp/stealth_test.png"
        await browser.page.screenshot(path=screenshot_path, full_page=True)
        results["screenshot"] = screenshot_path
        logger.info(f"Screenshot saved to {screenshot_path}")

    except Exception as e:
        results["status"] = "FAIL"
        results["error"] = str(e)
        logger.error(f"Stealth test failed: {e}")
    finally:
        if browser:
            await browser.stop()

    return results


async def test_brave_search():
    """Test Brave Search with various queries"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Brave Search Tests")
    logger.info("=" * 60)

    results = {"test": "Brave Search", "status": "PENDING", "queries": []}

    test_queries = [
        "python programming tutorial",
        "machine learning basics",
        "latest technology news",
    ]

    browser = None
    try:
        browser = BrowserManager()
        await browser.start()

        tools = BraveSearchTools(browser.page)

        all_passed = True
        for query in test_queries:
            query_result = {
                "query": query,
                "status": "PENDING",
                "result_count": 0,
                "sample_results": [],
            }

            try:
                logger.info(f"\nTesting query: '{query}'")
                search_results = await tools.search(query, count=5)

                query_result["result_count"] = len(search_results)
                query_result["sample_results"] = [
                    {"title": r.title, "url": r.url} for r in search_results[:3]
                ]

                if len(search_results) > 0:
                    query_result["status"] = "PASS"
                    logger.info(f"  ✓ Found {len(search_results)} results")
                    for i, r in enumerate(search_results[:3], 1):
                        logger.info(f"    {i}. {r.title[:60]}...")
                else:
                    query_result["status"] = "FAIL"
                    all_passed = False
                    logger.error(f"  ✗ No results found")

            except Exception as e:
                query_result["status"] = "FAIL"
                query_result["error"] = str(e)
                all_passed = False
                logger.error(f"  ✗ Error: {e}")

            results["queries"].append(query_result)

        results["status"] = "PASS" if all_passed else "FAIL"

    except Exception as e:
        results["status"] = "FAIL"
        results["error"] = str(e)
        logger.error(f"Brave Search test failed: {e}")
    finally:
        if browser:
            await browser.stop()

    return results


async def test_content_extraction():
    """Test content extraction on a news article"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Content Extraction Test")
    logger.info("=" * 60)

    results = {"test": "Content Extraction", "status": "PENDING", "details": {}}

    # Use a reliable article for testing
    test_url = "https://en.wikipedia.org/wiki/Python_(programming_language)"

    browser = None
    try:
        browser = BrowserManager()
        await browser.start()

        tools = BraveSearchTools(browser.page)

        logger.info(f"Extracting content from: {test_url}")
        extracted = await tools.extract(test_url, max_length=3000)

        results["details"]["url"] = test_url
        results["details"]["title"] = extracted.title
        results["details"]["word_count"] = extracted.word_count
        results["details"]["has_summary"] = extracted.summary is not None
        results["details"]["content_sample"] = (
            extracted.content[:500] + "..." if len(extracted.content) > 500 else extracted.content
        )

        # Validate extraction
        checks = []
        if extracted.title and len(extracted.title) > 5:
            checks.append("✓ Title extracted")
        else:
            checks.append("✗ Title missing or too short")

        if extracted.word_count > 100:
            checks.append(f"✓ Substantial content ({extracted.word_count} words)")
        else:
            checks.append(f"✗ Content too short ({extracted.word_count} words)")

        if extracted.summary:
            checks.append("✓ Summary generated")
        else:
            checks.append("✗ No summary")

        # Check for clean content (no obvious noise)
        noise_indicators = ["cookie", "subscribe", "advertisement", "privacy policy"]
        noise_found = [n for n in noise_indicators if n.lower() in extracted.content.lower()[:500]]

        if not noise_found:
            checks.append("✓ No obvious noise in opening content")
        else:
            checks.append(f"⚠ Possible noise detected: {noise_found}")

        results["details"]["checks"] = checks

        # Determine pass/fail
        critical_passes = sum(1 for c in checks if c.startswith("✓"))
        if critical_passes >= 3:
            results["status"] = "PASS"
        else:
            results["status"] = "WARNING"

        for check in checks:
            logger.info(f"  {check}")

        logger.info(f"\n  Title: {extracted.title}")
        logger.info(f"  Words: {extracted.word_count}")

    except Exception as e:
        results["status"] = "FAIL"
        results["error"] = str(e)
        logger.error(f"Content extraction test failed: {e}")
    finally:
        if browser:
            await browser.stop()

    return results


async def run_all_tests():
    """Run all integration tests"""
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 6: INTEGRATION TESTS")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    all_results = {"timestamp": datetime.now().isoformat(), "tests": []}

    # Test 1: Stealth
    stealth_results = await test_stealth()
    all_results["tests"].append(stealth_results)

    # Test 2: Brave Search
    search_results = await test_brave_search()
    all_results["tests"].append(search_results)

    # Test 3: Content Extraction
    extraction_results = await test_content_extraction()
    all_results["tests"].append(extraction_results)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    total = len(all_results["tests"])
    passed = sum(1 for t in all_results["tests"] if t["status"] == "PASS")
    warnings = sum(1 for t in all_results["tests"] if t["status"] == "WARNING")
    failed = sum(1 for t in all_results["tests"] if t["status"] == "FAIL")

    logger.info(f"Total: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Warnings: {warnings}")
    logger.info(f"Failed: {failed}")

    for test in all_results["tests"]:
        icon = "✓" if test["status"] == "PASS" else "⚠" if test["status"] == "WARNING" else "✗"
        logger.info(f"  {icon} {test['test']}: {test['status']}")

    return all_results


if __name__ == "__main__":
    results = asyncio.run(run_all_tests())

    # Save results to file
    import json

    with open("/tmp/integration_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\nDetailed results saved to: /tmp/integration_test_results.json")
