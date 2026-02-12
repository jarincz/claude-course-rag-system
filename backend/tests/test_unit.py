"""Unit tests — every external dependency is mocked."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from backend.session_manager import SessionManager
from backend.vector_store import SearchResults, VectorStore
from backend.search_tools import ToolManager, CourseSearchTool, Tool
from backend.document_processor import DocumentProcessor
from backend.models import Lesson, Course, CourseChunk


# ===================================================================
# TestSessionManager
# ===================================================================

class TestSessionManager:
    def test_create_session_returns_unique_ids(self, session_manager):
        s1 = session_manager.create_session()
        s2 = session_manager.create_session()
        assert s1 != s2

    def test_create_session_increments_counter(self, session_manager):
        s1 = session_manager.create_session()
        s2 = session_manager.create_session()
        assert s1 == "session_1"
        assert s2 == "session_2"

    def test_add_message_to_new_session(self, session_manager):
        session_manager.add_message("unknown_session", "user", "hello")
        history = session_manager.get_conversation_history("unknown_session")
        assert history is not None
        assert "hello" in history

    def test_add_exchange_adds_both_messages(self, session_manager):
        sid = session_manager.create_session()
        session_manager.add_exchange(sid, "question?", "answer!")
        assert len(session_manager.sessions[sid]) == 2
        assert session_manager.sessions[sid][0].role == "user"
        assert session_manager.sessions[sid][1].role == "assistant"

    def test_get_history_formats_correctly(self, session_manager):
        sid = session_manager.create_session()
        session_manager.add_exchange(sid, "What is AI?", "AI is intelligence.")
        history = session_manager.get_conversation_history(sid)
        assert "User: What is AI?" in history
        assert "Assistant: AI is intelligence." in history

    def test_get_history_returns_none_for_unknown_session(self, session_manager):
        assert session_manager.get_conversation_history("nonexistent") is None

    def test_get_history_returns_none_for_empty_session(self, session_manager):
        sid = session_manager.create_session()
        assert session_manager.get_conversation_history(sid) is None

    def test_history_trimming(self, session_manager):
        """With max_history=2, after 5 exchanges only last 4 messages kept."""
        sid = session_manager.create_session()
        for i in range(5):
            session_manager.add_exchange(sid, f"q{i}", f"a{i}")
        # max_history=2 → keeps last 2*2=4 messages
        assert len(session_manager.sessions[sid]) == 4

    def test_clear_session(self, session_manager):
        sid = session_manager.create_session()
        session_manager.add_exchange(sid, "q", "a")
        session_manager.clear_session(sid)
        assert session_manager.get_conversation_history(sid) is None


# ===================================================================
# TestSearchResults
# ===================================================================

class TestSearchResults:
    def test_from_chroma_with_results(self):
        chroma_results = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"course_title": "A"}, {"course_title": "B"}]],
            "distances": [[0.1, 0.2]],
        }
        sr = SearchResults.from_chroma(chroma_results)
        assert sr.documents == ["doc1", "doc2"]
        assert len(sr.metadata) == 2
        assert sr.error is None

    def test_from_chroma_with_empty(self):
        chroma_results = {"documents": [], "metadatas": [], "distances": []}
        sr = SearchResults.from_chroma(chroma_results)
        assert sr.is_empty()

    def test_empty_factory(self):
        sr = SearchResults.empty("something went wrong")
        assert sr.error == "something went wrong"
        assert sr.documents == []
        assert sr.is_empty()

    def test_is_empty_false(self):
        sr = SearchResults(documents=["hello"], metadata=[{}], distances=[0.1])
        assert not sr.is_empty()


# ===================================================================
# TestBuildFilter
# ===================================================================

class TestBuildFilter:
    """Test VectorStore._build_filter as a static-like method."""

    def _build(self, course_title, lesson_number):
        return VectorStore._build_filter(None, course_title, lesson_number)

    def test_no_filters(self):
        assert self._build(None, None) is None

    def test_course_only(self):
        assert self._build("My Course", None) == {"course_title": "My Course"}

    def test_lesson_only(self):
        assert self._build(None, 3) == {"lesson_number": 3}

    def test_both(self):
        result = self._build("My Course", 1)
        assert result == {"$and": [{"course_title": "My Course"}, {"lesson_number": 1}]}

    def test_lesson_zero_is_valid(self):
        """lesson_number=0 must be treated as a valid filter (not falsy)."""
        result = self._build(None, 0)
        assert result == {"lesson_number": 0}


# ===================================================================
# TestToolManager
# ===================================================================

class TestToolManager:
    def _make_dummy_tool(self, name="dummy"):
        tool = MagicMock(spec=Tool)
        tool.get_tool_definition.return_value = {"name": name, "description": "test"}
        tool.execute.return_value = "result"
        return tool

    def test_register_tool(self):
        tm = ToolManager()
        tool = self._make_dummy_tool("my_tool")
        tm.register_tool(tool)
        assert "my_tool" in tm.tools

    def test_register_tool_without_name_raises(self):
        tm = ToolManager()
        tool = MagicMock(spec=Tool)
        tool.get_tool_definition.return_value = {"description": "no name"}
        with pytest.raises(ValueError):
            tm.register_tool(tool)

    def test_get_definitions(self):
        tm = ToolManager()
        tm.register_tool(self._make_dummy_tool("t1"))
        tm.register_tool(self._make_dummy_tool("t2"))
        defs = tm.get_tool_definitions()
        assert len(defs) == 2

    def test_execute_found(self):
        tm = ToolManager()
        tool = self._make_dummy_tool("t1")
        tm.register_tool(tool)
        result = tm.execute_tool("t1", query="hello")
        tool.execute.assert_called_once_with(query="hello")
        assert result == "result"

    def test_execute_not_found(self):
        tm = ToolManager()
        result = tm.execute_tool("nonexistent")
        assert "not found" in result

    def test_get_last_sources_with_data(self):
        tm = ToolManager()
        tool = self._make_dummy_tool("t1")
        tool.last_sources = [{"text": "source1"}]
        tm.register_tool(tool)
        assert tm.get_last_sources() == [{"text": "source1"}]

    def test_get_last_sources_empty(self):
        tm = ToolManager()
        tool = self._make_dummy_tool("t1")
        tool.last_sources = []
        tm.register_tool(tool)
        assert tm.get_last_sources() == []

    def test_reset_sources(self):
        tm = ToolManager()
        tool = self._make_dummy_tool("t1")
        tool.last_sources = [{"text": "src"}]
        tm.register_tool(tool)
        tm.reset_sources()
        assert tool.last_sources == []


# ===================================================================
# TestCourseSearchTool
# ===================================================================

class TestCourseSearchTool:
    def test_tool_definition_structure(self, mock_vector_store):
        tool = CourseSearchTool(mock_vector_store)
        defn = tool.get_tool_definition()
        assert defn["name"] == "search_course_content"
        assert "query" in defn["input_schema"]["properties"]
        assert defn["input_schema"]["required"] == ["query"]

    def test_execute_with_results(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=["doc about AI"],
            metadata=[{"course_title": "AI 101", "lesson_number": 1}],
            distances=[0.1],
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com/l1"
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="what is AI")
        assert "AI 101" in result
        assert "doc about AI" in result

    def test_execute_empty_results(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="nothing here", course_name="XYZ")
        assert "No relevant content found" in result

    def test_execute_with_error(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults.empty("No course found matching 'XYZ'")
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test", course_name="XYZ")
        assert "No course found" in result

    def test_source_tracking_with_links(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=["content"],
            metadata=[{"course_title": "C1", "lesson_number": 1}],
            distances=[0.1],
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com/l1"
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["link"] == "https://example.com/l1"

    def test_source_tracking_without_links(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=["content"],
            metadata=[{"course_title": "C1", "lesson_number": None}],
            distances=[0.1],
        )
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")
        assert len(tool.last_sources) == 1
        assert "link" not in tool.last_sources[0]


# ===================================================================
# TestDocumentProcessor
# ===================================================================

class TestDocumentProcessor:
    def test_chunk_text_basic(self):
        dp = DocumentProcessor(chunk_size=50, chunk_overlap=0)
        text = "First sentence here. Second sentence here. Third one is also here."
        chunks = dp.chunk_text(text)
        assert len(chunks) >= 1
        # All content should be present across chunks
        combined = " ".join(chunks)
        assert "First sentence" in combined

    def test_chunk_text_with_overlap(self):
        dp = DocumentProcessor(chunk_size=60, chunk_overlap=20)
        text = "Alpha sentence. Beta sentence. Gamma sentence. Delta sentence."
        chunks = dp.chunk_text(text)
        assert len(chunks) >= 1

    def test_chunk_text_empty(self):
        dp = DocumentProcessor(chunk_size=100, chunk_overlap=10)
        chunks = dp.chunk_text("")
        assert chunks == []

    def test_process_course_document_full(self, tmp_path):
        doc = tmp_path / "course.txt"
        doc.write_text(
            "Course Title: Test Course\n"
            "Course Link: https://example.com\n"
            "Course Instructor: Prof. X\n"
            "\n"
            "Lesson 1: Introduction\n"
            "Lesson Link: https://example.com/l1\n"
            "This is the content of lesson one. It covers basics of the topic.\n"
            "\n"
            "Lesson 2: Advanced Topics\n"
            "Lesson Link: https://example.com/l2\n"
            "This is the content of lesson two. It covers advanced material.\n"
        )
        dp = DocumentProcessor(chunk_size=800, chunk_overlap=100)
        course, chunks = dp.process_course_document(str(doc))
        assert course.title == "Test Course"
        assert course.instructor == "Prof. X"
        assert course.course_link == "https://example.com"
        assert len(course.lessons) == 2
        assert len(chunks) >= 2

    def test_process_course_document_no_lessons(self, tmp_path):
        doc = tmp_path / "plain.txt"
        doc.write_text(
            "Course Title: Plain Doc\n"
            "Course Link: https://example.com\n"
            "Course Instructor: Nobody\n"
            "\n"
            "Just some text content without any lesson markers at all.\n"
        )
        dp = DocumentProcessor(chunk_size=800, chunk_overlap=100)
        course, chunks = dp.process_course_document(str(doc))
        assert course.title == "Plain Doc"
        assert len(course.lessons) == 0
        assert len(chunks) >= 1


# ===================================================================
# TestModels
# ===================================================================

class TestModels:
    def test_lesson_creation(self):
        lesson = Lesson(lesson_number=1, title="Intro")
        assert lesson.lesson_number == 1
        assert lesson.lesson_link is None

    def test_course_creation_with_defaults(self):
        course = Course(title="My Course")
        assert course.course_link is None
        assert course.instructor is None
        assert course.lessons == []

    def test_course_chunk_creation(self):
        chunk = CourseChunk(content="hello", course_title="C", chunk_index=0)
        assert chunk.lesson_number is None
        assert chunk.content == "hello"
