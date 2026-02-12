"""Integration tests — Claude API always mocked, multi-component interactions tested."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from anthropic.types import TextBlock, ToolUseBlock, Usage, Message

from backend.ai_generator import AIGenerator
from backend.search_tools import ToolManager, CourseSearchTool
from backend.vector_store import SearchResults
from backend.rag_system import RAGSystem
from backend.session_manager import SessionManager


# ===================================================================
# TestAIGenerator
# ===================================================================

class TestAIGenerator:
    """All tests mock anthropic.Anthropic so no real API calls are made."""

    @pytest.fixture
    def ai_gen(self, make_claude_message):
        """AIGenerator with a mocked Anthropic client."""
        with patch("backend.ai_generator.anthropic.Anthropic") as MockClient:
            gen = AIGenerator(api_key="sk-ant-fake", model="claude-sonnet-4-20250514")
            self._mock_client = gen.client
            self._make_msg = make_claude_message
            yield gen

    def test_direct_answer(self, ai_gen, make_claude_message):
        ai_gen.client.messages.create.return_value = make_claude_message(text="Hello world")
        result = ai_gen.generate_response(query="Say hello")
        assert result == "Hello world"
        call_kwargs = ai_gen.client.messages.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0
        assert call_kwargs["max_tokens"] == 800

    def test_with_conversation_history(self, ai_gen, make_claude_message):
        ai_gen.client.messages.create.return_value = make_claude_message(text="ok")
        ai_gen.generate_response(query="follow up", conversation_history="User: hi\nAssistant: hey")
        call_kwargs = ai_gen.client.messages.create.call_args.kwargs
        assert "Previous conversation:" in call_kwargs["system"]

    def test_with_tools(self, ai_gen, make_claude_message):
        ai_gen.client.messages.create.return_value = make_claude_message(text="answer")
        tools = [{"name": "search_course_content", "description": "search", "input_schema": {}}]
        ai_gen.generate_response(query="q", tools=tools)
        call_kwargs = ai_gen.client.messages.create.call_args.kwargs
        assert "tools" in call_kwargs
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_triggers_tool_execution(self, ai_gen, make_claude_message):
        """Mock Claude to return tool_use first, then text. Verify tool called and two API calls."""
        tool_response = make_claude_message(
            tool_use={"id": "toolu_01", "name": "search_course_content", "input": {"query": "AI"}}
        )
        final_response = make_claude_message(text="AI is great")
        ai_gen.client.messages.create.side_effect = [tool_response, final_response]

        tm = ToolManager()
        mock_tool = MagicMock()
        mock_tool.get_tool_definition.return_value = {"name": "search_course_content"}
        mock_tool.execute.return_value = "search results here"
        tm.register_tool(mock_tool)

        tools = tm.get_tool_definitions()
        result = ai_gen.generate_response(query="What is AI?", tools=tools, tool_manager=tm)

        assert result == "AI is great"
        mock_tool.execute.assert_called_once_with(query="AI")
        assert ai_gen.client.messages.create.call_count == 2

    def test_tool_execution_message_chain(self, ai_gen, make_claude_message):
        """Second call messages: [user msg, assistant tool_use, user tool_result]."""
        tool_response = make_claude_message(
            tool_use={"id": "toolu_02", "name": "search_course_content", "input": {"query": "MCP"}}
        )
        final_response = make_claude_message(text="MCP explained")
        ai_gen.client.messages.create.side_effect = [tool_response, final_response]

        tm = ToolManager()
        mock_tool = MagicMock()
        mock_tool.get_tool_definition.return_value = {"name": "search_course_content"}
        mock_tool.execute.return_value = "tool output"
        tm.register_tool(mock_tool)

        ai_gen.generate_response(query="What is MCP?", tools=tm.get_tool_definitions(), tool_manager=tm)

        second_call_kwargs = ai_gen.client.messages.create.call_args_list[1].kwargs
        messages = second_call_kwargs["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        # Third message contains tool results
        assert messages[2]["role"] == "user"
        assert messages[2]["content"][0]["type"] == "tool_result"

    def test_followup_includes_tools_when_under_max_rounds(self, ai_gen, make_claude_message):
        """Second messages.create call (round 1) SHOULD have 'tools' key since round 1 < MAX_TOOL_ROUNDS."""
        tool_response = make_claude_message(
            tool_use={"id": "toolu_03", "name": "search_course_content", "input": {"query": "test"}}
        )
        final_response = make_claude_message(text="done")
        ai_gen.client.messages.create.side_effect = [tool_response, final_response]

        tm = ToolManager()
        mock_tool = MagicMock()
        mock_tool.get_tool_definition.return_value = {"name": "search_course_content"}
        mock_tool.execute.return_value = "results"
        tm.register_tool(mock_tool)

        ai_gen.generate_response(query="q", tools=tm.get_tool_definitions(), tool_manager=tm)

        second_call_kwargs = ai_gen.client.messages.create.call_args_list[1].kwargs
        assert "tools" in second_call_kwargs


# ===================================================================
# TestRAGSystemQuery
# ===================================================================

class TestRAGSystemQuery:
    """Tests RAGSystem.query with mocked sub-components."""

    @pytest.fixture
    def rag(self, test_config):
        """RAGSystem with mocked VectorStore and AIGenerator."""
        with patch("backend.rag_system.VectorStore") as MockVS, \
             patch("backend.rag_system.AIGenerator") as MockAI, \
             patch("backend.rag_system.DocumentProcessor"):
            rag = RAGSystem(test_config)
            self._mock_ai = rag.ai_generator
            self._mock_vs = rag.vector_store
            yield rag

    def test_query_with_tool_flow(self, rag):
        """When AI generator uses tool, sources are populated and session updated."""
        rag.ai_generator.generate_response.return_value = "AI answer"
        # Simulate the search tool having set sources
        rag.search_tool.last_sources = [{"text": "Test Course - Lesson 1"}]

        sid = rag.session_manager.create_session()
        answer, sources = rag.query("What is AI?", session_id=sid)

        assert answer == "AI answer"
        assert len(sources) == 1
        assert sources[0]["text"] == "Test Course - Lesson 1"
        # Session should be updated
        history = rag.session_manager.get_conversation_history(sid)
        assert "AI answer" in history

    def test_query_without_tool_flow(self, rag):
        """Direct answer with no tool usage — sources empty."""
        rag.ai_generator.generate_response.return_value = "Direct answer"
        # No sources set (tool not used)
        rag.search_tool.last_sources = []

        answer, sources = rag.query("What is 2+2?", session_id=None)
        assert answer == "Direct answer"
        assert sources == []

    def test_query_resets_sources(self, rag):
        """After query(), sources on the tool manager are cleared."""
        rag.ai_generator.generate_response.return_value = "answer"
        rag.search_tool.last_sources = [{"text": "src"}]

        rag.query("q", session_id=None)
        # Sources should have been reset
        assert rag.search_tool.last_sources == []


# ===================================================================
# TestAPIEndpoints
# ===================================================================

class TestAPIEndpoints:
    """Test FastAPI endpoints with mocked rag_system."""

    @pytest.fixture
    async def client(self):
        from httpx import AsyncClient, ASGITransport
        # Patch rag_system at module level before importing app
        with patch("backend.app.RAGSystem") as MockRAG, \
             patch("backend.app.config"):
            from backend.app import app
            mock_rag = MockRAG.return_value
            mock_rag.session_manager = SessionManager(max_history=2)
            mock_rag.query.return_value = ("Test answer", [{"text": "Source 1"}])
            mock_rag.get_course_analytics.return_value = {
                "total_courses": 4,
                "course_titles": ["Course A", "Course B", "Course C", "Course D"],
            }
            # Patch the module-level rag_system reference
            import backend.app as app_module
            app_module.rag_system = mock_rag

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac

    @pytest.mark.asyncio
    async def test_post_query_200(self, client):
        resp = await client.post("/api/query", json={"query": "hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

    @pytest.mark.asyncio
    async def test_get_courses_200(self, client):
        resp = await client.get("/api/courses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 4
        assert len(data["course_titles"]) == 4
