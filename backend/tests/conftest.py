"""Shared fixtures for the RAG system test suite."""

import os
import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from backend.config import Config
from backend.session_manager import SessionManager
from backend.models import Course, Lesson, CourseChunk
from backend.vector_store import VectorStore


# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def test_config(tmp_path):
    """Config with fake API key and tmp_path ChromaDB."""
    return Config(
        ANTHROPIC_API_KEY="sk-ant-test-fake-key-000",
        ANTHROPIC_MODEL="claude-sonnet-4-20250514",
        EMBEDDING_MODEL="all-MiniLM-L6-v2",
        CHUNK_SIZE=800,
        CHUNK_OVERLAP=100,
        MAX_RESULTS=5,
        MAX_HISTORY=2,
        CHROMA_PATH=str(tmp_path / "chroma_test"),
    )


# ---------------------------------------------------------------------------
# Session manager fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def session_manager():
    """Fresh SessionManager with max_history=2."""
    return SessionManager(max_history=2)


# ---------------------------------------------------------------------------
# Sample course data
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_course_data():
    """Return (Course, List[CourseChunk]) with 2 lessons and 3 chunks."""
    course = Course(
        title="Test Course: Intro to AI",
        course_link="https://example.com/course",
        instructor="Dr. Smith",
        lessons=[
            Lesson(lesson_number=1, title="What is AI?", lesson_link="https://example.com/lesson1"),
            Lesson(lesson_number=2, title="Neural Networks", lesson_link="https://example.com/lesson2"),
        ],
    )
    chunks = [
        CourseChunk(
            content="Artificial intelligence is the simulation of human intelligence.",
            course_title="Test Course: Intro to AI",
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="Neural networks are computing systems inspired by biological neural networks.",
            course_title="Test Course: Intro to AI",
            lesson_number=2,
            chunk_index=1,
        ),
        CourseChunk(
            content="Deep learning uses multiple layers to progressively extract features.",
            course_title="Test Course: Intro to AI",
            lesson_number=2,
            chunk_index=2,
        ),
    ]
    return course, chunks


# ---------------------------------------------------------------------------
# Real VectorStore backed by a temp ChromaDB (for integration tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def vector_store_with_data(tmp_path, sample_course_data):
    """Real ChromaDB in a temp dir, preloaded with sample data."""
    course, chunks = sample_course_data
    store = VectorStore(
        chroma_path=str(tmp_path / "chroma_int"),
        embedding_model="all-MiniLM-L6-v2",
        max_results=5,
    )
    store.add_course_metadata(course)
    store.add_course_content(chunks)
    return store


# ---------------------------------------------------------------------------
# Mock VectorStore (avoids heavy model loading in pure-unit tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_vector_store():
    """A MagicMock that quacks like VectorStore."""
    store = MagicMock(spec=VectorStore)
    store.max_results = 5
    return store


# ---------------------------------------------------------------------------
# Factory for Anthropic Message objects
# ---------------------------------------------------------------------------

@pytest.fixture
def make_claude_message():
    """Factory that builds real anthropic.types.Message objects.

    Usage:
        msg = make_claude_message(text="Hello")
        msg = make_claude_message(tool_use={"id": "t1", "name": "search_course_content", "input": {"query": "AI"}})
        msg = make_claude_message(blocks=[TextBlock(...), ToolUseBlock(...)])
    """
    from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

    def _factory(
        *,
        text: str | None = None,
        tool_use: dict | None = None,
        blocks: list | None = None,
        stop_reason: str = "end_turn",
        model: str = "claude-sonnet-4-20250514",
    ) -> Message:
        if blocks is not None:
            content = blocks
        elif tool_use is not None:
            content = [
                ToolUseBlock(
                    id=tool_use.get("id", "toolu_test_001"),
                    type="tool_use",
                    name=tool_use["name"],
                    input=tool_use["input"],
                )
            ]
            stop_reason = "tool_use"
        else:
            content = [TextBlock(type="text", text=text or "")]

        return Message(
            id="msg_test_001",
            type="message",
            role="assistant",
            content=content,
            model=model,
            stop_reason=stop_reason,
            usage=Usage(input_tokens=10, output_tokens=20, cache_creation_input_tokens=0, cache_read_input_tokens=0),
        )

    return _factory
