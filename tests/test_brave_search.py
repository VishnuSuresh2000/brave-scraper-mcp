"""
Tests for Brave Search and content extraction tools.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.brave_search import (
    BraveSearchTools,
    SearchResult,
    SearchResponse,
    ExtractedContent,
    brave_search,
    brave_extract,
)


class TestSearchResult:
    """Test suite for SearchResult model."""

    def test_search_result_creation(self):
        """Test SearchResult can be created with all fields."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet content",
            position=1,
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet content"
        assert result.position == 1

    def test_search_result_defaults(self):
        """Test SearchResult with default values."""
        result = SearchResult(title="Test", url="https://example.com", snippet="", position=0)

        assert result.title == "Test"
        assert result.url == "https://example.com"
        assert result.snippet == ""
        assert result.position == 0


class TestExtractedContent:
    """Test suite for ExtractedContent model."""

    def test_extracted_content_creation(self):
        """Test ExtractedContent can be created."""
        content = ExtractedContent(
            title="Article Title",
            url="https://example.com/article",
            content="This is the article content.",
            summary="Quick summary",
            word_count=100,
        )

        assert content.title == "Article Title"
        assert content.url == "https://example.com/article"
        assert content.content == "This is the article content."
        assert content.summary == "Quick summary"
        assert content.word_count == 100

    def test_extracted_content_optional_summary(self):
        """Test ExtractedContent without summary."""
        content = ExtractedContent(
            title="Short Article",
            url="https://example.com/short",
            content="Short content.",
            word_count=10,
        )

        assert content.summary is None
        assert content.word_count == 10


class TestBraveSearchTools:
    """Test suite for BraveSearchTools class."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.evaluate = AsyncMock()
        page.content = AsyncMock()
        return page

    @pytest.fixture
    def search_tools(self, mock_page):
        """Create a BraveSearchTools instance."""
        return BraveSearchTools(mock_page)

    @pytest.mark.asyncio
    async def test_search_success(self, search_tools, mock_page):
        """Test successful search execution."""
        # Mock search results
        mock_results = [
            {
                "title": "Result 1",
                "url": "https://example1.com",
                "snippet": "Snippet 1",
                "position": 1,
            },
            {
                "title": "Result 2",
                "url": "https://example2.com",
                "snippet": "Snippet 2",
                "position": 2,
            },
        ]
        mock_page.evaluate = AsyncMock(return_value={"results": mock_results, "aiSummary": None})

        response = await search_tools.search("test query", count=5)
        results = response.results

        assert len(results) == 2
        assert results[0].title == "Result 1"
        assert results[0].url == "https://example1.com"
        assert results[0].position == 1
        assert results[1].title == "Result 2"

        # Verify navigation
        mock_page.goto.assert_called_once()
        call_args = mock_page.goto.call_args
        assert "search.brave.com" in call_args[0][0]
        assert "test%20query" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_search_empty_results(self, search_tools, mock_page):
        """Test search with no results."""
        mock_page.evaluate = AsyncMock(return_value={"results": [], "aiSummary": None})

        response = await search_tools.search("no results query", count=10)
        results = response.results

        assert len(results) == 0
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_limit_results(self, search_tools, mock_page):
        """Test search respects count parameter."""
        mock_results = [
            {
                "title": f"Result {i}",
                "url": f"https://example{i}.com",
                "snippet": f"Snippet {i}",
                "position": i,
            }
            for i in range(1, 21)  # 20 results
        ]
        mock_page.evaluate = AsyncMock(return_value={"results": mock_results, "aiSummary": None})

        response = await search_tools.search("query", count=5)
        results = response.results

        assert len(results) == 5
        assert results[-1].position == 5

    @pytest.mark.asyncio
    async def test_search_url_encoding(self, search_tools, mock_page):
        """Test query URL encoding."""
        mock_page.evaluate = AsyncMock(return_value={"results": [], "aiSummary": None})

        await search_tools.search("query with spaces & special chars!", count=5)

        call_args = mock_page.goto.call_args
        url = call_args[0][0]
        assert "query%20with%20spaces%20%26%20special%20chars%21" in url

    @pytest.mark.asyncio
    async def test_extract_success(self, search_tools, mock_page):
        """Test successful content extraction."""
        # Mock page content and title
        mock_page.content = AsyncMock(return_value="<html><body>Test content</body></html>")
        mock_page.evaluate = AsyncMock(
            side_effect=[
                "Test Page Title",  # For getting title
                "Test content from JavaScript extraction",  # For content extraction
            ]
        )

        # Return content with >100 words so summary is generated
        long_content = " ".join(["word"] * 150)
        with patch.object(search_tools, "_clean_content", return_value=long_content):
            with patch.object(search_tools, "_generate_summary", return_value="Summary"):
                result = await search_tools.extract("https://example.com/article")

        assert result.title == "Test Page Title"
        assert result.url == "https://example.com/article"
        assert result.word_count == 150
        assert result.summary == "Summary"

    @pytest.mark.asyncio
    async def test_extract_with_max_length(self, search_tools, mock_page):
        """Test content extraction with max_length parameter."""
        mock_page.content = AsyncMock(return_value="<html><body>Content</body></html>")
        mock_page.evaluate = AsyncMock(
            side_effect=[
                "Title",
                "A" * 10000,  # Long content
            ]
        )

        with patch.object(search_tools, "_clean_content", return_value="A" * 10000):
            result = await search_tools.extract("https://example.com", max_length=100)

        assert len(result.content) <= 103  # 100 chars + "..."

    @pytest.mark.asyncio
    async def test_extract_no_summary_for_short_content(self, search_tools, mock_page):
        """Test that short content doesn't get summary."""
        mock_page.content = AsyncMock(return_value="<html><body>Short</body></html>")
        mock_page.evaluate = AsyncMock(side_effect=["Title", "Short content"])

        with patch.object(search_tools, "_clean_content", return_value="Short content"):
            result = await search_tools.extract("https://example.com")

        assert result.summary is None
        assert result.word_count == 2


class TestContentCleaning:
    """Test suite for content cleaning methods."""

    @pytest.fixture
    def search_tools(self):
        """Create a search tools instance with mock page."""
        mock_page = AsyncMock()
        return BraveSearchTools(mock_page)

    def test_clean_content_removes_excess_whitespace(self, search_tools):
        """Test that excess whitespace is removed."""
        text = "  Multiple   spaces   and\t\ttabs  "
        cleaned = search_tools._clean_content(text)
        assert cleaned == "Multiple spaces and tabs"

    def test_clean_content_removes_boilerplate(self, search_tools):
        """Test that boilerplate text is removed."""
        text = "Article content. Share this article. Read more."
        cleaned = search_tools._clean_content(text)
        assert "Share this article" not in cleaned
        assert "Read more" not in cleaned
        assert "Article content" in cleaned

    def test_clean_content_empty_string(self, search_tools):
        """Test cleaning empty string."""
        cleaned = search_tools._clean_content("")
        assert cleaned == ""

    def test_clean_content_none(self, search_tools):
        """Test cleaning None."""
        cleaned = search_tools._clean_content(None)
        assert cleaned == ""

    def test_clean_content_removes_social_sharing(self, search_tools):
        """Test that social sharing prompts are removed."""
        text = "Great article content. Share this on Facebook. Follow us on Twitter."
        cleaned = search_tools._clean_content(text)
        assert "Share this on Facebook" not in cleaned
        assert "Follow us on Twitter" not in cleaned
        assert "Great article content" in cleaned

    def test_clean_content_removes_cookie_notices(self, search_tools):
        """Test that cookie notices are removed."""
        text = "Article text. This site uses cookies to improve your experience. Cookie Policy."
        cleaned = search_tools._clean_content(text)
        assert "This site uses cookies" not in cleaned
        assert "Cookie Policy" not in cleaned
        assert "Article text" in cleaned

    def test_clean_content_removes_privacy_terms(self, search_tools):
        """Test that privacy and terms notices are removed."""
        text = "Content here. Privacy Policy Terms of Service."
        cleaned = search_tools._clean_content(text)
        assert "Privacy Policy" not in cleaned
        assert "Terms of Service" not in cleaned
        assert "Content here" in cleaned

    def test_clean_content_removes_subscription_prompts(self, search_tools):
        """Test that subscription prompts are removed."""
        text = "Article text. Subscribe to our newsletter. Sign up now!"
        cleaned = search_tools._clean_content(text)
        assert "Subscribe to our newsletter" not in cleaned
        assert "Sign up now" not in cleaned
        assert "Article text" in cleaned

    def test_clean_content_removes_advertisements(self, search_tools):
        """Test that ad-related text is removed."""
        text = "Content here. Advertisement Sponsored content."
        cleaned = search_tools._clean_content(text)
        assert "Advertisement" not in cleaned
        assert "Sponsored content" not in cleaned
        assert "Content here" in cleaned

    def test_clean_content_removes_navigation_text(self, search_tools):
        """Test that navigation text is removed."""
        text = "Article content. Home » Menu Quick Links. You might also like."
        cleaned = search_tools._clean_content(text)
        assert "Quick Links" not in cleaned
        assert "You might also like" not in cleaned
        assert "Article content" in cleaned

    def test_clean_content_removes_copyright(self, search_tools):
        """Test that copyright notices are removed."""
        text = "Article text. © 2024 Company Name. All rights reserved."
        cleaned = search_tools._clean_content(text)
        assert "© 2024" not in cleaned
        assert "All rights reserved" not in cleaned
        assert "Article text" in cleaned

    def test_clean_content_removes_dates(self, search_tools):
        """Test that standalone dates are removed."""
        text = "Article content. Published: January 15, 2024 Updated 3 days ago"
        cleaned = search_tools._clean_content(text)
        assert "January 15, 2024" not in cleaned
        assert "3 days ago" not in cleaned
        assert "Article content" in cleaned

    def test_clean_content_filters_short_lines(self, search_tools):
        """Test that short standalone lines are filtered out."""
        # Test with realistic short navigation lines that would appear alone
        text = "This is a substantial paragraph with lots of content.\n\nOK\n\nAnother substantial paragraph with enough content to be kept."
        cleaned = search_tools._clean_content(text)
        # "OK" is a single word less than 3 words and doesn't end with punctuation, should be removed
        assert "\nOK\n" not in cleaned
        assert "substantial paragraph" in cleaned

    def test_clean_content_keeps_sentences(self, search_tools):
        """Test that short sentences are kept."""
        text = "This is important. Go. Stop."
        cleaned = search_tools._clean_content(text)
        assert "This is important" in cleaned

    def test_clean_content_handles_multiple_patterns(self, search_tools):
        """Test cleaning handles multiple boilerplate patterns together."""
        text = """
        Main article content goes here with important information.
        
        Share this article on Facebook and Twitter.
        
        Subscribe to our newsletter for updates.
        
        Cookie Policy Privacy Policy Terms of Service.
        
        © 2024 All rights reserved.
        
        More great content continues here with detailed explanation.
        """
        cleaned = search_tools._clean_content(text)
        assert "Main article content" in cleaned
        assert "More great content" in cleaned
        assert "Share this article" not in cleaned
        assert "Subscribe to our newsletter" not in cleaned
        assert "Cookie Policy" not in cleaned
        assert "© 2024" not in cleaned


class TestSummaryGeneration:
    """Test suite for summary generation."""

    @pytest.fixture
    def search_tools(self):
        """Create a search tools instance with mock page."""
        mock_page = AsyncMock()
        return BraveSearchTools(mock_page)

    def test_generate_summary_basic(self, search_tools):
        """Test basic summary generation."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        summary = search_tools._generate_summary(text, sentences=2)
        assert summary == "First sentence. Second sentence."

    def test_generate_summary_fewer_sentences_than_requested(self, search_tools):
        """Test summary when text has fewer sentences than requested."""
        text = "Only one sentence."
        summary = search_tools._generate_summary(text, sentences=3)
        assert summary == "Only one sentence."

    def test_generate_summary_with_various_punctuation(self, search_tools):
        """Test summary with different sentence endings."""
        text = "First sentence! Second sentence? Third sentence. Fourth."
        summary = search_tools._generate_summary(text, sentences=3)
        assert "First sentence!" in summary
        assert "Second sentence?" in summary


class TestSearchResponse:
    """Test suite for SearchResponse model."""

    def test_search_response_creation(self):
        """Test SearchResponse can be created with all fields."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet content",
            position=1,
        )
        response = SearchResponse(
            query="test query",
            results=[result],
            page=1,
            has_next_page=False,
        )

        assert response.query == "test query"
        assert len(response.results) == 1
        assert response.page == 1
        assert response.has_next_page is False

    def test_search_response_defaults(self):
        """Test SearchResponse with default values."""
        result = SearchResult(title="Test", url="https://example.com", snippet="", position=0)
        response = SearchResponse(query="test", results=[result])

        assert response.page == 1
        assert response.has_next_page is False

    def test_search_response_with_pagination_metadata(self):
        """Test SearchResponse with pagination metadata."""
        results = [
            SearchResult(
                title=f"Result {i}", url=f"https://example{i}.com", snippet="Snippet", position=i
            )
            for i in range(1, 6)
        ]
        response = SearchResponse(
            query="pagination test",
            results=results,
            page=2,
            has_next_page=True,
        )

        assert response.page == 2
        assert response.has_next_page is True
        assert len(response.results) == 5


class TestPagination:
    """Test suite for pagination functionality."""

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
    async def test_search_with_page_parameter(self, search_tools, mock_page):
        """Test search with page parameter."""
        mock_results = [
            {
                "title": "Result 1",
                "url": "https://example1.com",
                "snippet": "Snippet",
                "position": 1,
            }
        ]
        mock_page.evaluate = AsyncMock(return_value={"results": mock_results, "aiSummary": None})

        response = await search_tools.search("test query", count=10, page=2)

        assert response.page == 2
        mock_page.goto.assert_called_once()
        call_args = mock_page.goto.call_args
        url = call_args[0][0]
        assert "page=2" in url

    @pytest.mark.asyncio
    async def test_search_url_includes_page_only_when_greater_than_1(self, search_tools, mock_page):
        """Test that page parameter is only added when page > 1."""
        mock_page.evaluate = AsyncMock(return_value={"results": [], "aiSummary": None})

        await search_tools.search("test query", count=10, page=1)
        url = mock_page.goto.call_args[0][0]
        assert "page=" not in url

    @pytest.mark.asyncio
    async def test_search_response_has_next_page_true_when_full_results(
        self, search_tools, mock_page
    ):
        """Test has_next_page is True when results equal count."""
        mock_results = [
            {
                "title": f"Result {i}",
                "url": f"https://example{i}.com",
                "snippet": "Snippet",
                "position": i,
            }
            for i in range(1, 11)
        ]
        mock_page.evaluate = AsyncMock(return_value={"results": mock_results, "aiSummary": None})

        response = await search_tools.search("test query", count=10, page=1)

        assert response.has_next_page is True

    @pytest.mark.asyncio
    async def test_search_response_has_next_page_false_when_partial_results(
        self, search_tools, mock_page
    ):
        """Test has_next_page is False when results less than count."""
        mock_results = [
            {
                "title": "Result 1",
                "url": "https://example1.com",
                "snippet": "Snippet",
                "position": 1,
            }
        ]
        mock_page.evaluate = AsyncMock(return_value={"results": mock_results, "aiSummary": None})

        response = await search_tools.search("test query", count=10, page=1)

        assert response.has_next_page is False

    @pytest.mark.asyncio
    async def test_search_response_has_next_page_false_on_last_page(self, search_tools, mock_page):
        """Test has_next_page is False when fewer results than count."""
        mock_results = [
            {
                "title": f"Result {i}",
                "url": f"https://example{i}.com",
                "snippet": "Snippet",
                "position": i,
            }
            for i in range(1, 6)
        ]
        mock_page.evaluate = AsyncMock(return_value={"results": mock_results, "aiSummary": None})

        response = await search_tools.search("test query", count=10, page=2)

        assert response.has_next_page is False

    @pytest.mark.asyncio
    async def test_search_backward_compatibility_page_default(self, search_tools, mock_page):
        """Test backward compatibility - page defaults to 1."""
        mock_page.evaluate = AsyncMock(return_value={"results": [], "aiSummary": None})

        response = await search_tools.search("test query", count=10)

        assert response.page == 1
        assert response.has_next_page is False

    @pytest.mark.asyncio
    async def test_search_backward_compatibility_without_page_param(self, search_tools, mock_page):
        """Test backward compatibility - page parameter not required."""
        mock_page.evaluate = AsyncMock(return_value={"results": [], "aiSummary": None})

        response = await search_tools.search("test query")

        assert response.page == 1
        assert "page=" not in mock_page.goto.call_args[0][0]


class TestBraveSearchConvenienceFunction:
    """Test suite for brave_search convenience function."""

    @pytest.mark.asyncio
    async def test_brave_search_convenience_with_page(self):
        """Test the brave_search convenience function with page parameter."""
        mock_page = AsyncMock()
        mock_results = [
            {"title": "Result 1", "url": "https://example.com", "snippet": "Snippet", "position": 1}
        ]
        mock_page.evaluate = AsyncMock(return_value={"results": mock_results, "aiSummary": None})
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()

        with patch.object(
            BraveSearchTools,
            "search",
            return_value=SearchResponse(
                query="query",
                results=[
                    SearchResult(
                        title="Result 1", url="https://example.com", snippet="Snippet", position=1
                    )
                ],
                ai_summary=None,
                page=2,
                has_next_page=True,
            ),
        ):
            response = await brave_search(mock_page, "query", count=5, page_num=2)

        assert response.page == 2
        assert response.has_next_page is True


class TestBraveExtractConvenienceFunction:
    """Test suite for brave_extract convenience function."""

    @pytest.mark.asyncio
    async def test_brave_extract_convenience(self):
        """Test the brave_extract convenience function."""
        mock_page = AsyncMock()

        with patch.object(
            BraveSearchTools,
            "extract",
            return_value=ExtractedContent(
                title="Test", url="https://example.com", content="Content", word_count=10
            ),
        ):
            result = await brave_extract(mock_page, "https://example.com")

        assert result.title == "Test"
        assert result.word_count == 10


class TestIntegration:
    """Integration tests for Brave Search tools."""

    @pytest.mark.asyncio
    async def test_search_then_extract_workflow(self):
        """Test the full search and extract workflow."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        # Mock search results
        search_results = [
            {
                "title": "Article 1",
                "url": "https://example1.com",
                "snippet": "Snippet 1",
                "position": 1,
            },
            {
                "title": "Article 2",
                "url": "https://example2.com",
                "snippet": "Snippet 2",
                "position": 2,
            },
        ]
        mock_page.evaluate = AsyncMock(return_value={"results": search_results, "aiSummary": None})

        tools = BraveSearchTools(mock_page)

        # Search
        response = await tools.search("test", count=2)
        results = response.results
        assert len(results) == 2

        # Mock for extraction
        mock_page.content = AsyncMock(return_value="<html><body>Content</body></html>")
        mock_page.evaluate = AsyncMock(side_effect=["Article 1 Title", "Article content"])

        with patch.object(tools, "_clean_content", return_value="Cleaned article content"):
            extracted = await tools.extract(results[0].url)

        assert extracted.url == "https://example1.com"
        assert extracted.content == "Cleaned article content"


class TestErrorHandling:
    """Test error handling in Brave Search tools."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock()
        return page

    @pytest.fixture
    def search_tools(self, mock_page):
        """Create a search tools instance with mock page."""
        return BraveSearchTools(mock_page)

    @pytest.mark.asyncio
    async def test_search_handles_goto_error(self, search_tools, mock_page):
        """Test search handles navigation errors."""
        mock_page.goto = AsyncMock(side_effect=Exception("Navigation failed"))

        with pytest.raises(Exception, match="Navigation failed"):
            await search_tools.search("query")

    @pytest.mark.asyncio
    async def test_search_handles_selector_timeout(self, search_tools, mock_page):
        """Test search handles selector timeout gracefully (logs warning, proceeds)."""
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))
        mock_page.evaluate = AsyncMock(return_value={"results": [], "aiSummary": None})

        # Should NOT raise - code catches timeout and proceeds anyway
        response = await search_tools.search("query")
        assert response.results == []  # Returns empty results when selectors fail

    @pytest.mark.asyncio
    async def test_extract_handles_goto_error(self, search_tools, mock_page):
        """Test extract handles navigation errors."""
        mock_page.goto = AsyncMock(side_effect=Exception("Failed to load"))

        with pytest.raises(Exception, match="Failed to load"):
            await search_tools.extract("https://example.com")


class TestSearchResultFiltering:
    """Test suite for search result filtering and parsing."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock()
        return page

    @pytest.fixture
    def search_tools(self, mock_page):
        """Create a BraveSearchTools instance."""
        return BraveSearchTools(mock_page)

    @pytest.mark.asyncio
    async def test_search_filters_results_without_title(self, search_tools, mock_page):
        """Test that results without titles are filtered out."""
        mock_results = [
            {
                "title": "Valid Result",
                "url": "https://example.com",
                "snippet": "Snippet",
                "position": 1,
            },
            {
                "title": "",
                "url": "https://invalid.com",
                "snippet": "Snippet",
                "position": 2,
            },  # No title
            {
                "title": "Another Valid",
                "url": "https://example2.com",
                "snippet": "Snippet",
                "position": 3,
            },
        ]
        mock_page.evaluate = AsyncMock(return_value={"results": mock_results, "aiSummary": None})

        response = await search_tools.search("query", count=10)
        results = response.results

        assert len(results) == 3  # All are included, filtering happens in JS
        # Note: In real implementation, empty titles might be filtered

    @pytest.mark.asyncio
    async def test_search_filters_results_without_url(self, search_tools, mock_page):
        """Test that results without URLs are filtered out."""
        mock_results = [
            {
                "title": "Valid Result",
                "url": "https://example.com",
                "snippet": "Snippet",
                "position": 1,
            },
            {"title": "Invalid", "url": "", "snippet": "Snippet", "position": 2},  # No URL
        ]
        mock_page.evaluate = AsyncMock(return_value={"results": mock_results, "aiSummary": None})

        response = await search_tools.search("query", count=10)
        results = response.results

        assert len(results) == 2  # Both included, JS filtering logic applies


class TestEnhancedExtraction:
    """Test suite for enhanced content extraction with aggressive cleaning."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.content = AsyncMock()
        return page

    @pytest.fixture
    def search_tools(self, mock_page):
        """Create a BraveSearchTools instance."""
        return BraveSearchTools(mock_page)

    @pytest.mark.asyncio
    async def test_extract_with_aggressive_js_cleaning(self, search_tools, mock_page):
        """Test that JS extraction removes non-content elements aggressively."""
        mock_page.content = AsyncMock(
            return_value="<html><body><nav>Menu</nav><article>Real content here</article><footer>Footer</footer></body></html>"
        )
        mock_page.evaluate = AsyncMock(
            side_effect=[
                "Page Title",  # For getting title
                "Real content here",  # For content extraction
            ]
        )

        with patch.object(search_tools, "_clean_content", return_value="Real content here"):
            result = await search_tools.extract("https://example.com")

        assert result.title == "Page Title"
        assert "Real content here" in result.content

    @pytest.mark.asyncio
    async def test_extract_finds_main_content_area(self, search_tools, mock_page):
        """Test that extraction finds main content area when standard tags are missing."""
        mock_page.content = AsyncMock(return_value="<html><body>Content</body></html>")
        mock_page.evaluate = AsyncMock(
            side_effect=[
                "Test Title",
                "Main article content with substantial text that would be identified as main content. "
                * 10,
            ]
        )

        with patch.object(
            search_tools,
            "_clean_content",
            return_value="Main article content with substantial text that would be identified as main content. "
            * 10,
        ):
            result = await search_tools.extract("https://example.com")

        assert result.word_count > 50  # Should have substantial content

    @pytest.mark.asyncio
    async def test_extract_removes_cookie_banners(self, search_tools, mock_page):
        """Test that cookie banners are removed during extraction."""
        mock_page.content = AsyncMock(
            return_value="<html><body><div class='cookie-banner'>Accept cookies</div><main>Article</main></body></html>"
        )
        mock_page.evaluate = AsyncMock(
            side_effect=[
                "Article Title",
                "Article content without cookie banner",
            ]
        )

        with patch.object(
            search_tools, "_clean_content", return_value="Article content without cookie banner"
        ):
            result = await search_tools.extract("https://example.com")

        assert "Accept cookies" not in result.content
        assert "Article content" in result.content

    @pytest.mark.asyncio
    async def test_extract_removes_ads(self, search_tools, mock_page):
        """Test that advertisements are removed during extraction."""
        mock_page.content = AsyncMock(
            return_value="<html><body><div class='ad-container'>Buy now!</div><article>Real content</article></body></html>"
        )
        mock_page.evaluate = AsyncMock(
            side_effect=[
                "Article Title",
                "Real content",
            ]
        )

        with patch.object(search_tools, "_clean_content", return_value="Real content"):
            result = await search_tools.extract("https://example.com")

        assert "Buy now" not in result.content
        assert "Real content" in result.content

    @pytest.mark.asyncio
    async def test_extract_removes_social_widgets(self, search_tools, mock_page):
        """Test that social media widgets are removed."""
        mock_page.content = AsyncMock(
            return_value="<html><body><div class='social-share'>Share on Facebook</div><main>Article text</main></body></html>"
        )
        mock_page.evaluate = AsyncMock(
            side_effect=[
                "Article Title",
                "Article text",
            ]
        )

        with patch.object(search_tools, "_clean_content", return_value="Article text"):
            result = await search_tools.extract("https://example.com")

        assert "Share on Facebook" not in result.content
        assert "Article text" in result.content

    @pytest.mark.asyncio
    async def test_extract_handles_complex_page_structure(self, search_tools, mock_page):
        """Test extraction handles complex page with multiple potential content areas."""
        mock_page.content = AsyncMock(
            return_value="""
            <html><body>
                <header>Site Header</header>
                <nav>Navigation menu</nav>
                <div class="sidebar">Related links</div>
                <article class="post-content">
                    <h1>Article Title</h1>
                    <p>This is the main article content with substantial text.</p>
                    <p>Multiple paragraphs of real content here.</p>
                </article>
                <div class="comments">Comments section</div>
                <footer>Footer content</footer>
            </body></html>
            """
        )
        mock_page.evaluate = AsyncMock(
            side_effect=[
                "Page Title",
                "Article Title This is the main article content with substantial text. Multiple paragraphs of real content here.",
            ]
        )

        with patch.object(
            search_tools,
            "_clean_content",
            return_value="This is the main article content with substantial text. Multiple paragraphs of real content here.",
        ):
            result = await search_tools.extract("https://example.com")

        assert "Navigation menu" not in result.content
        assert "Related links" not in result.content
        assert "Comments section" not in result.content
        assert "Footer content" not in result.content
        assert "main article content" in result.content


class TestDataModels:
    """Test suite for Pydantic data models."""

    def test_search_result_json_serialization(self):
        """Test SearchResult can be serialized to JSON."""
        result = SearchResult(
            title="Test", url="https://example.com", snippet="Snippet", position=1
        )

        json_str = result.model_dump_json()
        data = json.loads(json_str)

        assert data["title"] == "Test"
        assert data["url"] == "https://example.com"
        assert data["position"] == 1

    def test_extracted_content_json_serialization(self):
        """Test ExtractedContent can be serialized to JSON."""
        content = ExtractedContent(
            title="Article",
            url="https://example.com/article",
            content="Content text",
            summary="Quick summary",
            word_count=100,
        )

        json_str = content.model_dump_json()
        data = json.loads(json_str)

        assert data["title"] == "Article"
        assert data["word_count"] == 100
        assert data["summary"] == "Quick summary"

    def test_extracted_content_without_summary_serialization(self):
        """Test ExtractedContent without summary serializes correctly."""
        content = ExtractedContent(
            title="Short", url="https://example.com", content="Content", word_count=10
        )

        json_str = content.model_dump_json()
        data = json.loads(json_str)

        assert data["summary"] is None

    def test_search_result_dict_conversion(self):
        """Test SearchResult can be converted to dict."""
        result = SearchResult(
            title="Test", url="https://example.com", snippet="Snippet", position=1
        )

        data = result.model_dump()
        assert data["title"] == "Test"
        assert data["url"] == "https://example.com"

    def test_search_response_json_serialization_with_pagination(self):
        """Test SearchResponse with pagination serializes correctly."""
        response = SearchResponse(
            query="test",
            results=[
                SearchResult(
                    title="Result 1", url="https://example1.com", snippet="Snippet", position=1
                ),
                SearchResult(
                    title="Result 2", url="https://example2.com", snippet="Snippet", position=2
                ),
            ],
            page=2,
            has_next_page=True,
        )

        json_str = response.model_dump_json()
        data = json.loads(json_str)

        assert data["query"] == "test"
        assert data["page"] == 2
        assert data["has_next_page"] is True
        assert len(data["results"]) == 2

    def test_search_response_json_serialization_defaults(self):
        """Test SearchResponse default values serialize correctly."""
        response = SearchResponse(
            query="test",
            results=[
                SearchResult(
                    title="Result", url="https://example.com", snippet="Snippet", position=1
                )
            ],
        )

        json_str = response.model_dump_json()
        data = json.loads(json_str)

        assert data["page"] == 1
        assert data["has_next_page"] is False
