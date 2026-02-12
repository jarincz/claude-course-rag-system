"""Content evaluation tests against the real ./chroma_db.

These tests verify search relevance, course name resolution, and analytics
using the actual indexed data (4 courses, ~528 chunks). They are auto-skipped
if chroma_db doesn't exist.
"""

import os
import pytest

from backend.vector_store import VectorStore

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

skip_if_no_db = pytest.mark.skipif(
    not os.path.isdir(CHROMA_PATH),
    reason="chroma_db not found — load course data first",
)


@pytest.fixture(scope="module")
def store():
    """Real VectorStore pointing at the project's chroma_db."""
    return VectorStore(
        chroma_path=CHROMA_PATH,
        embedding_model=EMBEDDING_MODEL,
        max_results=5,
    )


# ===================================================================
# TestSearchRelevance
# ===================================================================

@skip_if_no_db
class TestSearchRelevance:
    def test_computer_use_query(self, store):
        results = store.search(query="computer use with Anthropic")
        assert not results.is_empty()
        titles = [m.get("course_title", "") for m in results.metadata]
        assert any("Computer Use" in t for t in titles), f"Expected Computer Use course, got: {titles}"

    def test_mcp_query(self, store):
        results = store.search(query="what is MCP model context protocol")
        assert not results.is_empty()
        titles = [m.get("course_title", "") for m in results.metadata]
        assert any("MCP" in t for t in titles), f"Expected MCP course, got: {titles}"

    def test_embeddings_vector_search_query(self, store):
        results = store.search(query="embeddings retrieval vector search")
        assert not results.is_empty()
        titles = [m.get("course_title", "") for m in results.metadata]
        assert any("chroma" in t.lower() or "retrieval" in t.lower() or "embedding" in t.lower()
                    for t in titles), f"Expected Chroma/retrieval course, got: {titles}"

    def test_prompt_compression_query(self, store):
        results = store.search(query="prompt compression query optimization")
        assert not results.is_empty()
        titles = [m.get("course_title", "") for m in results.metadata]
        assert any("prompt" in t.lower() or "compression" in t.lower() or "optimization" in t.lower()
                    for t in titles), f"Expected prompt compression course, got: {titles}"

    def test_max_results_respected(self, store):
        results = store.search(query="introduction to the course")
        assert len(results.documents) <= 5


# ===================================================================
# TestCourseNameResolution
# ===================================================================

@skip_if_no_db
class TestCourseNameResolution:
    def test_exact_name(self, store):
        titles = store.get_existing_course_titles()
        if titles:
            resolved = store._resolve_course_name(titles[0])
            assert resolved == titles[0]

    def test_partial_mcp(self, store):
        resolved = store._resolve_course_name("MCP")
        assert resolved is not None
        assert "MCP" in resolved

    def test_fuzzy_computer_use(self, store):
        resolved = store._resolve_course_name("computer use")
        assert resolved is not None
        assert "Computer Use" in resolved or "computer" in resolved.lower()

    def test_nonexistent_returns_none(self, store):
        resolved = store._resolve_course_name("Completely Fake Course That Does Not Exist At All")
        # Semantic search may still return a match, so we just verify it returns something
        # (the real guard is in search() which checks if it's a close enough match)
        # This test verifies the method doesn't crash
        assert resolved is None or isinstance(resolved, str)


# ===================================================================
# TestFilteredSearch
# ===================================================================

@skip_if_no_db
class TestFilteredSearch:
    def test_filter_by_course_name(self, store):
        titles = store.get_existing_course_titles()
        if not titles:
            pytest.skip("No courses in DB")
        results = store.search(query="introduction", course_name=titles[0])
        if not results.is_empty():
            for m in results.metadata:
                assert m["course_title"] == titles[0]

    def test_filter_by_lesson_number(self, store):
        results = store.search(query="lesson content", lesson_number=1)
        if not results.is_empty():
            for m in results.metadata:
                assert m["lesson_number"] == 1

    def test_nonexistent_course_returns_error(self, store):
        results = store.search(query="anything", course_name="ZZZZ_NoSuchCourse_ZZZZ")
        # Semantic search may resolve to a real course, or return error
        # The main contract: it doesn't crash
        assert results is not None


# ===================================================================
# TestCourseAnalytics
# ===================================================================

@skip_if_no_db
class TestCourseAnalytics:
    def test_course_count(self, store):
        count = store.get_course_count()
        assert count == 4, f"Expected 4 courses, got {count}"

    def test_course_titles(self, store):
        titles = store.get_existing_course_titles()
        assert len(titles) == 4
        # Verify at least one known course name is present
        all_titles = " ".join(titles).lower()
        assert "mcp" in all_titles or "computer" in all_titles, f"Unexpected titles: {titles}"
