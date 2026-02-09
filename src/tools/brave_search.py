"""Brave Search and content extraction tools."""

import logging
from typing import List, Optional
from urllib.parse import quote

from pydantic import BaseModel
from patchright.async_api import Page

trafilatura = None
TRAFILATURA_AVAILABLE = False

try:
    import trafilatura as _trafilatura

    trafilatura = _trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """Model for search result data."""

    title: str
    url: str
    snippet: str
    position: int


class ExtractedContent(BaseModel):
    """Model for extracted content data."""

    title: str
    url: str
    content: str
    summary: Optional[str] = None
    word_count: int


class BraveSearchTools:
    """Tools for Brave Search and content extraction."""

    BRAVE_SEARCH_URL = "https://search.brave.com/search"

    def __init__(self, page: Page):
        self.page = page

    async def search(self, query: str, count: int = 10) -> List[SearchResult]:
        """Search Brave Search and return structured results.

        Args:
            query: Search query string
            count: Number of results to return (default: 10)

        Returns:
            List of SearchResult objects
        """
        logger.info(f"Searching Brave for: {query} (count={count})")

        # Navigate to Brave search with query
        encoded_query = quote(query)
        search_url = f"{self.BRAVE_SEARCH_URL}?q={encoded_query}"

        # Use domcontentloaded for faster navigation, then wait for results
        await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

        # Wait for page to be more stable
        await self.page.wait_for_timeout(3000)

        # Wait for search results to load with increased timeout
        # Brave Search is a SPA, so we need to wait for JavaScript rendering
        try:
            # Primary: Wait for any link with external URL
            await self.page.wait_for_selector("a[href^='https://www.'], a[href^='https://en.'], a[href^='http']", timeout=20000)
            logger.info("Found external links on page")
        except Exception as e:
            logger.warning(f"Could not find expected search result selectors: {e}")

        # Extract search results using JavaScript with multiple fallback strategies
        results = await self.page.evaluate(
            f"""
            () => {{
                const results = [];
                const seenUrls = new Set();

                // Strategy 1: Try Brave Search specific selectors (newest structure)
                // Look for result items in the main content area
                const braveSelectors = [
                    // Primary Brave Search structure
                    '#results .snippet',
                    '.snippet',
                    'div[data-loc="main"] > div > div',
                    'main article',
                    'article[data-loc]',
                    // Fallback generic
                    '.search-result',
                    '.result-item',
                    '[data-component="search-result"]'
                ];

                let resultElements = [];
                for (const sel of braveSelectors) {{
                    const elements = document.querySelectorAll(sel);
                    if (elements.length > 0) {{
                        resultElements = elements;
                        console.log('Found elements with selector:', sel, elements.length);
                        break;
                    }}
                }}

                // Strategy 2: If no structured results, find all external links
                if (resultElements.length === 0) {{
                    // Get all links that look like search results (external URLs)
                    const allLinks = Array.from(document.querySelectorAll('a[href^="https://"]'));
                    const searchLinks = allLinks.filter(a => {{
                        const href = a.href;
                        const text = a.textContent.trim();
                        // Filter out navigation, ads, and internal links
                        return href &&
                               text.length > 5 &&
                               !href.includes('search.brave.com') &&
                               !href.includes('brave.com/') &&
                               !href.includes('imgs.search.brave.com') &&
                               !href.includes('account.brave.com') &&
                               !a.closest('nav') &&
                               !a.closest('footer') &&
                               !a.querySelector('img[alt*="logo"]');  // Exclude logo links
                    }});

                    // Group by closest parent container to identify result blocks
                    const containers = new Map();
                    for (const link of searchLinks) {{
                        // Find the closest meaningful parent
                        let parent = link.closest('article, section, div[class*="result"], div[class*="item"], li');
                        if (!parent) {{
                            parent = link.parentElement?.parentElement?.parentElement;
                        }}
                        if (parent && !containers.has(parent)) {{
                            containers.set(parent, link);
                        }}
                    }}

                    resultElements = Array.from(containers.keys());
                    console.log('Found containers with links:', resultElements.length);
                }}

                // Extract results from elements
                for (let i = 0; i < Math.min(resultElements.length, {count}); i++) {{
                    const element = resultElements[i];
                    let title = '';
                    let url = '';
                    let snippet = '';

                    // Try to find title and URL
                    const titleLink = element.querySelector('a.l1') ||
                                     element.querySelector('a[href^="https://"]') ||
                                     element.querySelector('a[href^="http://"]') ||
                                     element.querySelector('a');
                    if (titleLink) {{
                        url = titleLink.href;
                        // Get title from .title class, h2, h3, or the link itself
                        const titleEl = titleLink.querySelector('.title') || 
                                        element.querySelector('h2, h3, [class*="title"]');
                        title = titleEl ? titleEl.textContent.trim() : titleLink.textContent.trim();
                    }}

                    // Try to find snippet/description
                    const snippetEl = element.querySelector('p, [class*="description"], [class*="snippet"], [data-loc="snippet"]');
                    if (snippetEl) {{
                        snippet = snippetEl.textContent.trim();
                    }}

                    // Validate and add result
                    if (title && url && !seenUrls.has(url) && url.startsWith('http')) {{
                        seenUrls.add(url);
                        results.push({{
                            title: title.substring(0, 200),  // Limit title length
                            url: url,
                            snippet: snippet.substring(0, 500),  // Limit snippet length
                            position: results.length + 1
                        }});
                    }}
                }}

                console.log('Extracted results:', results.length);
                return results;
            }}
            """
        )

        # Fallback: If still no results, try a simpler link extraction
        if not results:
            logger.warning("Primary extraction failed, trying simple link extraction")
            results = await self.page.evaluate(
                f"""
                () => {{
                    const results = [];
                    const seenUrls = new Set();

                    // Get all external links with meaningful text
                    const links = document.querySelectorAll('a[href^="https://"]');
                    for (let i = 0; i < links.length && results.length < {count}; i++) {{
                        const link = links[i];
                        const href = link.href;
                        const text = link.textContent.trim();

                        // Skip internal/irrelevant links
                        if (href.includes('brave.com') ||
                            href.includes('google.com') ||
                            text.length < 10 ||
                            seenUrls.has(href)) {{
                            continue;
                        }}

                        seenUrls.add(href);
                        results.push({{
                            title: text,
                            url: href,
                            snippet: '',
                            position: results.length + 1
                        }});
                    }}

                    return results;
                }}
                """
            )

        # Convert to SearchResult models
        search_results = []
        for i, result in enumerate(results[:count]):
            search_results.append(
                SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    snippet=result.get("snippet", ""),
                    position=result.get("position", i + 1),
                )
            )

        logger.info(f"Found {len(search_results)} search results")
        return search_results

    async def extract(self, url: str, max_length: int = 5000) -> ExtractedContent:
        """Extract clean content from a URL.

        Args:
            url: URL to extract content from
            max_length: Maximum content length (default: 5000)

        Returns:
            ExtractedContent object with clean text
        """
        logger.info(f"Extracting content from: {url}")

        # Navigate to the URL with better timeout handling
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await self.page.wait_for_timeout(2000)

        # Wait for content to load
        await self.page.wait_for_timeout(2000)

        # Try trafilatura first if available
        if TRAFILATURA_AVAILABLE and trafilatura is not None:
            try:
                html_content = await self.page.content()
                extracted = trafilatura.extract(
                    html_content,
                    include_comments=False,
                    include_tables=False,
                    no_fallback=False,
                    output_format="json",
                )

                if extracted:
                    import json

                    data = json.loads(extracted)
                    title = data.get("title", "")
                    text = data.get("text", "")

                    # Clean up the text
                    text = self._clean_content(text)

                    # Truncate if needed
                    if len(text) > max_length:
                        text = text[:max_length].rsplit(" ", 1)[0] + "..."

                    # Generate summary if content is long
                    summary = None
                    word_count = len(text.split())
                    if word_count > 100:
                        summary = self._generate_summary(text)

                    return ExtractedContent(
                        title=title or await self._get_page_title(),
                        url=url,
                        content=text,
                        summary=summary,
                        word_count=word_count,
                    )
            except Exception as e:
                logger.warning(f"Trafilatura extraction failed: {e}")

        # Fallback to JavaScript extraction
        return await self._extract_with_js(url, max_length)

    async def _extract_with_js(self, url: str, max_length: int) -> ExtractedContent:
        """Extract content using JavaScript as fallback with aggressive cleaning."""

        # Get page title
        title = await self._get_page_title()

        # Extract main content using heuristics with aggressive element removal
        content = await self.page.evaluate(
            """
            () => {
                // Create a clone of the body to manipulate without affecting the page
                const bodyClone = document.body.cloneNode(true);
                
                // Aggressively remove non-content elements by tag name
                const tagsToRemove = [
                    'script', 'style', 'nav', 'header', 'footer', 'aside',
                    'form', 'input', 'button', 'select', 'textarea',
                    'svg', 'canvas', 'video', 'audio', 'iframe', 'embed', 'object',
                    'noscript', 'template', 'dialog', 'menu', 'menuitem'
                ];
                
                tagsToRemove.forEach(tag => {
                    const elements = bodyClone.querySelectorAll(tag);
                    elements.forEach(el => el.remove());
                });
                
                // Remove elements by common class/ID patterns for ads and non-content
                const adSelectors = [
                    // Ads and sponsored content
                    '[class*="ad"]', '[id*="ad"]', '[class*="advertisement"]',
                    '[class*="sponsored"]', '[class*="promoted"]',
                    '[class*="partner"]', '[class*="affiliate"]',
                    
                    // Cookie banners and GDPR notices
                    '[class*="cookie"]', '[id*="cookie"]', 
                    '[class*="gdpr"]', '[id*="gdpr"]',
                    '[class*="consent"]', '[id*="consent"]',
                    '[class*="privacy"]', '[class*="banner"]',
                    
                    // Social media widgets
                    '[class*="social"]', '[class*="share"]', '[class*="follow"]',
                    '[id*="social"]', '[id*="share"]',
                    
                    // Sidebars and navigation
                    '[class*="sidebar"]', '[id*="sidebar"]',
                    '[class*="menu"]', '[class*="navigation"]', '[class*="nav"]',
                    '[class*="breadcrumb"]', '[id*="breadcrumb"]',
                    
                    // Comments and engagement
                    '[class*="comment"]', '[id*="comment"]',
                    '[class*="disqus"]', '[id*="disqus"]',
                    '[class*="reaction"]', '[class*="rating"]',
                    
                    // Related content widgets
                    '[class*="related"]', '[id*="related"]',
                    '[class*="recommended"]', '[class*="popular"]',
                    '[class*="trending"]', '[class*="more"]',
                    '[class*="read-more"]', '[class*="see-also"]',
                    
                    // Newsletter and subscription
                    '[class*="newsletter"]', '[id*="newsletter"]',
                    '[class*="subscribe"]', '[class*="subscription"]',
                    '[class*="signup"]', '[class*="sign-up"]',
                    
                    // Popups and modals
                    '[class*="popup"]', '[id*="popup"]',
                    '[class*="modal"]', '[id*="modal"]',
                    '[class*="overlay"]', '[id*="overlay"]',
                    '[class*="sticky"]', '[class*="fixed"]',
                    
                    // Author and metadata
                    '[class*="author"]', '[class*="byline"]',
                    '[class*="date"]', '[class*="timestamp"]',
                    '[class*="meta"]', '[class*="metadata"]',
                    
                    // Tags and categories
                    '[class*="tags"]', '[class*="categories"]',
                    '[class*="tag-cloud"]', '[class*="keywords"]'
                ];
                
                adSelectors.forEach(selector => {
                    try {
                        const elements = bodyClone.querySelectorAll(selector);
                        elements.forEach(el => {
                            // Don't remove if it might be main content
                            const text = el.textContent || '';
                            const isShort = text.length < 200;
                            const isLinkOnly = el.querySelectorAll('a').length > 0 && text.trim().split(/\\s+/).length < 10;
                            
                            if (isShort || isLinkOnly) {
                                el.remove();
                            }
                        });
                    } catch (e) {
                        // Ignore invalid selectors
                    }
                });
                
                // Remove elements with display:none or visibility:hidden
                const allElements = bodyClone.querySelectorAll('*');
                allElements.forEach(el => {
                    try {
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                            el.remove();
                        }
                    } catch (e) {
                        // Element might be removed already
                    }
                });
                
                // Try to find main content with priority order
                const contentSelectors = [
                    // High priority semantic tags
                    'article',
                    'main',
                    '[role="main"]',
                    
                    // Common content containers
                    '.content',
                    '#content',
                    '.main-content',
                    '#main-content',
                    '.post-content',
                    '.article-content',
                    '.entry-content',
                    '.page-content',
                    
                    // Blog/CMS specific
                    '.post-body',
                    '.entry-body',
                    '.article-body',
                    '[itemprop="articleBody"]',
                    
                    // News sites
                    '.story-body',
                    '.story-content',
                    '.news-content',
                    
                    // Generic fallbacks
                    '.body',
                    '#body',
                    '[class*="content"]',
                    '[id*="content"]'
                ];

                let mainContent = null;
                let bestContentLength = 0;
                
                // First pass: try to find by semantic tags
                for (const selector of contentSelectors) {
                    const el = bodyClone.querySelector(selector);
                    if (el) {
                        const textLength = (el.textContent || '').length;
                        // Prefer longer content if it's substantial
                        if (textLength > bestContentLength && textLength > 500) {
                            mainContent = el;
                            bestContentLength = textLength;
                        }
                    }
                }

                // Second pass: if no good semantic content found, use heuristic scoring
                if (!mainContent || bestContentLength < 500) {
                    const candidates = bodyClone.querySelectorAll('div, section');
                    let bestScore = 0;
                    
                    candidates.forEach(el => {
                        const text = el.textContent || '';
                        const textLength = text.length;
                        const paragraphs = el.querySelectorAll('p').length;
                        const links = el.querySelectorAll('a').length;
                        const linkDensity = links > 0 ? textLength / links : textLength;
                        
                        // Score based on: text length, paragraph count, and link density
                        // Higher score = more likely to be main content
                        const score = (textLength * 0.5) + (paragraphs * 100) + (linkDensity * 0.3);
                        
                        if (score > bestScore && textLength > 300) {
                            // Check it's not just a navigation container
                            const className = (el.className || '').toLowerCase();
                            const id = (el.id || '').toLowerCase();
                            const isNavRelated = /nav|menu|sidebar|header|footer|comment|related|meta/.test(className + ' ' + id);
                            
                            if (!isNavRelated || paragraphs > 3) {
                                bestScore = score;
                                mainContent = el;
                            }
                        }
                    });
                }

                // Final fallback to body if no main content found
                if (!mainContent) {
                    mainContent = bodyClone;
                }

                // Get text content and clean it up
                let text = mainContent.innerText || mainContent.textContent || '';
                
                // Remove very short lines (likely UI elements)
                const lines = text.split('\\n');
                const filteredLines = lines.filter(line => {
                    const trimmed = line.trim();
                    return trimmed.length > 10 || (trimmed.length > 0 && trimmed.includes('.'));
                });
                text = filteredLines.join('\\n');
                
                // Clean up whitespace
                text = text.replace(/\\s+/g, ' ').trim();
                
                // Remove standalone URLs
                text = text.replace(/https?:\\/\\/[^\\s]+/g, '');
                
                return text;
            }
            """
        )

        # Clean content with the improved cleaner
        content = self._clean_content(content)

        # Truncate if needed
        if len(content) > max_length:
            content = content[:max_length].rsplit(" ", 1)[0] + "..."

        word_count = len(content.split())

        # Generate summary if content is long
        summary = None
        if word_count > 100:
            summary = self._generate_summary(content)

        return ExtractedContent(
            title=title, url=url, content=content, summary=summary, word_count=word_count
        )

    async def _get_page_title(self) -> str:
        """Get the page title."""
        return await self.page.evaluate("document.title") or ""

    def _clean_content(self, text: str) -> str:
        """Clean up extracted content with aggressive boilerplate removal."""
        if not text:
            return ""

        import re

        # Remove excess whitespace and normalize
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)

        # Remove social sharing and engagement prompts
        social_patterns = [
            r"Share this\s*(article|post|page)?\s*(on\s+\w+)?",
            r"Share on\s+(Facebook|Twitter|LinkedIn|X|Instagram|Pinterest|Reddit)",
            r"Follow us\s*(on\s+\w+)?",
            r"Like us\s*(on\s+\w+)?",
            r"Connect with us",
            r"Join the conversation",
            r"Leave a comment",
            r"Add a comment",
            r"Post a comment",
            r"\d+\s*(likes?|shares?|comments?|reactions?)",
        ]

        for pattern in social_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove navigation and action prompts
        action_patterns = [
            r"Read more\s*(about this)?",
            r"Click here\s*(to\s+\w+)?",
            r"Learn more\s*(about)?",
            r"Find out more",
            r"Discover more",
            r"See more",
            r"View more",
            r"Show more",
            r"Expand\s*(for more)?",
            r"Continue reading",
            r"Skip to\s*(content|main|navigation)?",
            r"Jump to\s*\w+",
            r"Back to\s*(top|main|home)?",
            r"Go back",
            r"Next\s*(page|article|post)?",
            r"Previous\s*(page|article|post)?",
        ]

        for pattern in action_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove subscription prompts
        subscription_patterns = [
            r"Subscribe\s*(to\s+\w+)?\s*(now)?",
            r"Sign up\s*(for\s+\w+)?\s*(now)?",
            r"Join\s*(our)?\s*(newsletter|list|community)",
            r"Newsletter\s*(signup|sign-up|subscription)?",
            r"Get\s+\w+\s+delivered\s+to\s+your\s+inbox",
            r"Stay\s+(updated|informed|connected)",
            r"Never\s+miss\s+(a|an)\s+\w+",
        ]

        for pattern in subscription_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove cookie and privacy notices
        cookie_patterns = [
            r"Cookie\s*(Policy|Notice|Settings|Consent|Banner)?",
            r"This\s+site\s+uses\s+cookies",
            r"We\s+use\s+cookies\s+(to\s+\w+)?",
            r"By\s+(using|continuing|clicking)\s+.*?(you\s+agree|accept|consent)",
            r"Accept\s*(all)?\s*cookies",
            r"Cookie\s*preferences",
            r"Privacy\s*(Policy|Notice|Settings)",
            r"Terms\s*(of\s*Service|and\s*Conditions|of\s*Use)?",
            r"GDPR\s*compliance",
            r"California\s*Consumer\s*Privacy",
            r"Do\s*Not\s*Sell\s*My\s*Information",
        ]

        for pattern in cookie_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove common navigation text
        nav_patterns = [
            r"Home\s*»?\s*",
            r"Menu\s*" r"Navigation\s*",
            r"Site\s*Map",
            r"Sitemap",
            r"Search\s*(this\s*site)?",
            r"Quick\s*Links",
            r"Related\s*(Links|Pages|Articles|Posts)?",
            r"You\s*might\s*also\s*like",
            r"Recommended\s*(for\s*you)?",
            r"Popular\s*\w+",
            r"Trending\s*\w+",
            r"Most\s*(Read|Viewed|Popular)",
        ]

        for pattern in nav_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove ad-related text
        ad_patterns = [
            r"Advertisement\s*",
            r"Ad\s*\d*\s*",
            r"Sponsored\s*(content|post|link)?",
            r"Promoted\s*(content|post)?",
            r"Partner\s*content",
            r"Paid\s*(content|partnership)?",
            r"Affiliate\s*(link|disclosure)?",
        ]

        for pattern in ad_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove copyright and legal text
        legal_patterns = [
            r"©\s*\d{4}.*?(All\s+rights\s+reserved)?",
            r"Copyright\s*©?\s*\d{4}",
            r"All\s+rights\s+reserved",
            r"Trademark\s*(notice)?",
            r"Legal\s*(notice|disclaimer)",
            r"Disclaimer",
        ]

        for pattern in legal_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove timestamps and dates that appear alone
        date_patterns = [
            r"\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\d+\s+(minutes?|hours?|days?|weeks?|months?|years?)\s+ago",
            r"Updated?\s*:?\s*.*\d{4}",
            r"Published?\s*:?\s*.*\d{4}",
        ]

        for pattern in date_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove standalone short lines (likely navigation/UI elements)
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Keep lines that are substantive (more than 3 words or longer than 30 chars)
            if len(stripped.split()) > 3 or len(stripped) > 30:
                cleaned_lines.append(stripped)
            elif stripped and len(stripped) > 10:
                # Check if it looks like a sentence
                if stripped[0].isupper() and stripped[-1] in ".!?":
                    cleaned_lines.append(stripped)

        text = "\n".join(cleaned_lines)

        # Final cleanup
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)

        return text.strip()

    def _generate_summary(self, text: str, sentences: int = 3) -> str:
        """Generate a simple summary by extracting first N sentences."""
        import re

        # Split into sentences
        sentences_list = re.split(r"(?<=[.!?])\s+", text)

        # Take first N sentences
        summary_sentences = sentences_list[:sentences]

        return " ".join(summary_sentences)


# Convenience functions for direct usage
async def brave_search(page: Page, query: str, count: int = 10) -> List[SearchResult]:
    """Convenience function to search Brave.

    Args:
        page: Playwright page object
        query: Search query
        count: Number of results

    Returns:
        List of SearchResult objects
    """
    tools = BraveSearchTools(page)
    return await tools.search(query, count)


async def brave_extract(page: Page, url: str, max_length: int = 5000) -> ExtractedContent:
    """Convenience function to extract content.

    Args:
        page: Playwright page object
        url: URL to extract from
        max_length: Maximum content length

    Returns:
        ExtractedContent object
    """
    tools = BraveSearchTools(page)
    return await tools.extract(url, max_length)
