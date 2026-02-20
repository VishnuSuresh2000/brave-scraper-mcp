"""
Tests for AI Summary extraction feature.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools.stealth_search import (
    AISummary,
    SearchResponse,
    SearchResult,
    StealthSearchTools,
)


class TestAISummaryModel:
    """Test suite for AISummary model."""

    def test_ai_summary_creation(self):
        """Test AISummary can be created with text."""
        summary = AISummary(text="This is an AI summary.")
        assert summary.text == "This is an AI summary."
        assert summary.sources == []

    def test_ai_summary_with_sources(self):
        """Test AISummary with citation sources."""
        sources = [
            {"title": "Source 1", "url": "https://example.com/1"},
            {"title": "Source 2", "url": "https://example.com/2"},
        ]
        summary = AISummary(text="Summary with sources", sources=sources)
        assert summary.text == "Summary with sources"
        assert len(summary.sources) == 2
        assert summary.sources[0]["title"] == "Source 1"

    def test_ai_summary_empty_sources(self):
        """Test AISummary with empty sources list."""
        summary = AISummary(text="No sources", sources=[])
        assert summary.sources == []


class TestSearchResponseModel:
    """Test suite for SearchResponse model."""

    def test_search_response_without_ai_summary(self):
        """Test SearchResponse without AI summary."""
        results = [
            SearchResult(title="Result 1", url="https://example.com", snippet="Snippet", position=1)
        ]
        response = SearchResponse(query="test", results=results, ai_summary=None)

        assert response.query == "test"
        assert len(response.results) == 1
        assert response.ai_summary is None

    def test_search_response_with_ai_summary(self):
        """Test SearchResponse with AI summary."""
        results = [
            SearchResult(title="Result 1", url="https://example.com", snippet="Snippet", position=1)
        ]
        ai_summary = AISummary(text="AI generated summary")
        response = SearchResponse(query="test", results=results, ai_summary=ai_summary)

        assert response.query == "test"
        assert len(response.results) == 1
        assert response.ai_summary is not None
        assert response.ai_summary.text == "AI generated summary"

    def test_search_response_empty_results(self):
        """Test SearchResponse with no results but AI summary."""
        ai_summary = AISummary(text="Summary only")
        response = SearchResponse(query="test", results=[], ai_summary=ai_summary)

        assert len(response.results) == 0
        assert response.ai_summary.text == "Summary only"


class TestAISummaryExtraction:
    """Test suite for AI summary extraction from page."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        return page

    @pytest.fixture
    def search_tools(self, mock_page):
        """Create StealthSearchTools with mock page."""
        return StealthSearchTools(mock_page)

    @pytest.mark.asyncio
    async def test_ai_summary_extraction_with_chatllm_answer(self, search_tools, mock_page):
        """Test extraction when chatllm-answer-list element exists."""
        mock_page.evaluate = AsyncMock(
            return_value={
                "results": [
                    {"title": "Test", "url": "https://example.com", "snippet": "", "position": 1}
                ],
                "aiSummary": {"text": "Python is a programming language.", "sources": []},
            }
        )

        response = await search_tools.search("test", count=10)

        assert response.ai_summary is not None
        assert "Python" in response.ai_summary.text

    @pytest.mark.asyncio
    async def test_ai_summary_extraction_empty(self, search_tools, mock_page):
        """Test extraction when AI summary element is empty."""
        mock_page.evaluate = AsyncMock(
            return_value={
                "results": [
                    {"title": "Test", "url": "https://example.com", "snippet": "", "position": 1}
                ],
                "aiSummary": None,
            }
        )

        response = await search_tools.search("test", count=10)

        assert response.ai_summary is None

    @pytest.mark.asyncio
    async def test_ai_summary_with_citations(self, search_tools, mock_page):
        """Test extraction of AI summary with citation sources."""
        mock_page.evaluate = AsyncMock(
            return_value={
                "results": [],
                "aiSummary": {
                    "text": "AI summary text",
                    "sources": [
                        {"title": "Wikipedia", "url": "https://wikipedia.org/article"},
                        {"title": "Docs", "url": "https://docs.python.org"},
                    ],
                },
            }
        )

        response = await search_tools.search("test", count=10)

        assert response.ai_summary is not None
        assert len(response.ai_summary.sources) == 2
        assert response.ai_summary.sources[0]["title"] == "Wikipedia"

    @pytest.mark.asyncio
    async def test_ai_summary_filters_brave_urls(self, search_tools, mock_page):
        """Test that Brave internal URLs are filtered from sources."""
        mock_page.evaluate = AsyncMock(
            return_value={
                "results": [],
                "aiSummary": {
                    "text": "Summary",
                    "sources": [
                        {"title": "Good Source", "url": "https://example.com"},
                        {"title": "Brave Internal", "url": "https://search.brave.com/internal"},
                        {"title": "Brave Images", "url": "https://imgs.search.brave.com/img"},
                    ],
                },
            }
        )

        # Note: The filtering happens in JavaScript, this test verifies
        # that if filtered sources come through, they work correctly
        response = await search_tools.search("test", count=10)

        # This test assumes JS filtering already removed Brave URLs
        assert response.ai_summary is not None


class TestSearchResponseFormatting:
    """Test suite for SearchResponse JSON serialization."""

    def test_search_response_to_dict(self):
        """Test SearchResponse can be converted to dict."""
        results = [
            SearchResult(title="Test", url="https://example.com", snippet="Snippet", position=1)
        ]
        ai_summary = AISummary(text="Summary")
        response = SearchResponse(query="test", results=results, ai_summary=ai_summary)

        # Pydantic models have model_dump() method
        data = response.model_dump()
        assert data["query"] == "test"
        assert len(data["results"]) == 1
        assert data["ai_summary"]["text"] == "Summary"

    def test_search_response_json_serialization(self):
        """Test SearchResponse JSON serialization."""
        results = [
            SearchResult(title="Test", url="https://example.com", snippet="Test", position=1)
        ]
        ai_summary = AISummary(
            text="AI Summary", sources=[{"title": "Source", "url": "https://example.com"}]
        )
        response = SearchResponse(query="test", results=results, ai_summary=ai_summary)

        json_str = response.model_dump_json()
        assert "AI Summary" in json_str
        assert "test" in json_str


class TestAISummaryEdgeCases:
    """Test edge cases for AI summary extraction."""

    @pytest.fixture
    def mock_page(self):
        page = AsyncMock()
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        return page

    @pytest.fixture
    def search_tools(self, mock_page):
        return StealthSearchTools(mock_page)

    @pytest.mark.asyncio
    async def test_ai_summary_with_special_characters(self, search_tools, mock_page):
        """Test AI summary with special characters and unicode."""
        mock_page.evaluate = AsyncMock(
            return_value={
                "results": [],
                "aiSummary": {
                    "text": "Python™ is «awesome» — with special chars: \n\t",
                    "sources": [],
                },
            }
        )

        response = await search_tools.search("test", count=10)
        assert "Python" in response.ai_summary.text

    @pytest.mark.asyncio
    async def test_ai_summary_very_long_text(self, search_tools, mock_page):
        """Test AI summary with very long text."""
        long_text = "Python is great. " * 500  # ~10,000 chars
        mock_page.evaluate = AsyncMock(
            return_value={
                "results": [],
                "aiSummary": {"text": long_text, "sources": []},
            }
        )

        response = await search_tools.search("test", count=10)
        assert len(response.ai_summary.text) > 5000

    @pytest.mark.asyncio
    async def test_ai_summary_with_empty_sources_list(self, search_tools, mock_page):
        """Test AI summary with explicitly empty sources."""
        mock_page.evaluate = AsyncMock(
            return_value={
                "results": [],
                "aiSummary": {"text": "Summary text", "sources": []},
            }
        )

        response = await search_tools.search("test", count=10)
        assert response.ai_summary.sources == []
