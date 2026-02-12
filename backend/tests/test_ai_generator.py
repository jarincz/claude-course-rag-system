"""Tests for sequential tool calling in AIGenerator."""

import pytest
from unittest.mock import MagicMock, patch

from backend.ai_generator import AIGenerator
from backend.search_tools import ToolManager


def _make_tool_manager(execute_return="search results", execute_side_effect=None):
    """Helper: ToolManager with a single mock tool registered."""
    tm = ToolManager()
    mock_tool = MagicMock()
    mock_tool.get_tool_definition.return_value = {
        "name": "search_course_content",
        "description": "search",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }
    if execute_side_effect is not None:
        mock_tool.execute.side_effect = execute_side_effect
    else:
        mock_tool.execute.return_value = execute_return
    tm.register_tool(mock_tool)
    return tm, mock_tool


class TestSequentialToolCalling:
    """Tests for up to 2 sequential tool-call rounds."""

    @pytest.fixture
    def ai_gen(self):
        with patch("backend.ai_generator.anthropic.Anthropic"):
            yield AIGenerator(api_key="sk-ant-fake", model="claude-sonnet-4-20250514")

    def test_no_tool_call_returns_text_directly(self, ai_gen, make_claude_message):
        """When Claude responds with text, return it in a single API call."""
        ai_gen.client.messages.create.return_value = make_claude_message(text="Direct answer")
        tm, mock_tool = _make_tool_manager()

        result = ai_gen.generate_response(query="hello", tools=tm.get_tool_definitions(), tool_manager=tm)

        assert result == "Direct answer"
        assert ai_gen.client.messages.create.call_count == 1
        mock_tool.execute.assert_not_called()

    def test_single_tool_round(self, ai_gen, make_claude_message):
        """Claude uses tool once then responds with text — 2 API calls total."""
        tool_response = make_claude_message(
            tool_use={"id": "t1", "name": "search_course_content", "input": {"query": "AI"}}
        )
        text_response = make_claude_message(text="AI is great")
        ai_gen.client.messages.create.side_effect = [tool_response, text_response]

        tm, mock_tool = _make_tool_manager()
        result = ai_gen.generate_response(query="What is AI?", tools=tm.get_tool_definitions(), tool_manager=tm)

        assert result == "AI is great"
        assert ai_gen.client.messages.create.call_count == 2
        mock_tool.execute.assert_called_once_with(query="AI")

    def test_two_sequential_tool_rounds(self, ai_gen, make_claude_message):
        """Claude uses tool twice across two rounds — 3 API calls total."""
        tool_response_1 = make_claude_message(
            tool_use={"id": "t1", "name": "search_course_content", "input": {"query": "lesson 4 of course X"}}
        )
        tool_response_2 = make_claude_message(
            tool_use={"id": "t2", "name": "search_course_content", "input": {"query": "matching topic"}}
        )
        text_response = make_claude_message(text="Course Y matches")
        ai_gen.client.messages.create.side_effect = [tool_response_1, tool_response_2, text_response]

        tm, mock_tool = _make_tool_manager()
        result = ai_gen.generate_response(query="Find matching course", tools=tm.get_tool_definitions(), tool_manager=tm)

        assert result == "Course Y matches"
        assert ai_gen.client.messages.create.call_count == 3
        assert mock_tool.execute.call_count == 2

    def test_max_rounds_strips_tools(self, ai_gen, make_claude_message):
        """On round 2 (== MAX), tools are excluded from API params to force text response."""
        tool_response_1 = make_claude_message(
            tool_use={"id": "t1", "name": "search_course_content", "input": {"query": "q1"}}
        )
        tool_response_2 = make_claude_message(
            tool_use={"id": "t2", "name": "search_course_content", "input": {"query": "q2"}}
        )
        text_response = make_claude_message(text="final answer")
        ai_gen.client.messages.create.side_effect = [tool_response_1, tool_response_2, text_response]

        tm, _ = _make_tool_manager()
        ai_gen.generate_response(query="complex query", tools=tm.get_tool_definitions(), tool_manager=tm)

        # Round 1 follow-up (call index 1) should include tools
        round1_kwargs = ai_gen.client.messages.create.call_args_list[1].kwargs
        assert "tools" in round1_kwargs

        # Round 2 follow-up (call index 2) should NOT include tools
        round2_kwargs = ai_gen.client.messages.create.call_args_list[2].kwargs
        assert "tools" not in round2_kwargs

    def test_tool_exception_stops_chain(self, ai_gen, make_claude_message):
        """When tool execution raises an exception, error is sent to Claude and chain stops."""
        tool_response = make_claude_message(
            tool_use={"id": "t1", "name": "search_course_content", "input": {"query": "fail"}}
        )
        text_response = make_claude_message(text="Sorry, I encountered an issue")
        ai_gen.client.messages.create.side_effect = [tool_response, text_response]

        tm, _ = _make_tool_manager(execute_side_effect=Exception("DB connection failed"))
        result = ai_gen.generate_response(query="search", tools=tm.get_tool_definitions(), tool_manager=tm)

        assert result == "Sorry, I encountered an issue"
        assert ai_gen.client.messages.create.call_count == 2

        # Tools should be excluded from the follow-up (error stops chain)
        followup_kwargs = ai_gen.client.messages.create.call_args_list[1].kwargs
        assert "tools" not in followup_kwargs

        # Error message should be in the tool result sent to Claude
        tool_result_msg = followup_kwargs["messages"][2]["content"][0]["content"]
        assert "Tool execution error: DB connection failed" in tool_result_msg

    def test_tool_error_string_continues_chain(self, ai_gen, make_claude_message):
        """When tool returns an error string (no exception), chain continues normally."""
        tool_response_1 = make_claude_message(
            tool_use={"id": "t1", "name": "search_course_content", "input": {"query": "q1"}}
        )
        tool_response_2 = make_claude_message(
            tool_use={"id": "t2", "name": "search_course_content", "input": {"query": "q2"}}
        )
        text_response = make_claude_message(text="recovered answer")

        ai_gen.client.messages.create.side_effect = [tool_response_1, tool_response_2, text_response]

        # First call returns error string, second returns normal results
        tm, mock_tool = _make_tool_manager()
        mock_tool.execute.side_effect = ["No relevant content found.", "actual results"]

        result = ai_gen.generate_response(query="q", tools=tm.get_tool_definitions(), tool_manager=tm)

        assert result == "recovered answer"
        assert ai_gen.client.messages.create.call_count == 3
        assert mock_tool.execute.call_count == 2

    def test_message_history_preserved_across_rounds(self, ai_gen, make_claude_message):
        """Full message history is correctly threaded through both rounds."""
        tool_response_1 = make_claude_message(
            tool_use={"id": "t1", "name": "search_course_content", "input": {"query": "q1"}}
        )
        tool_response_2 = make_claude_message(
            tool_use={"id": "t2", "name": "search_course_content", "input": {"query": "q2"}}
        )
        text_response = make_claude_message(text="final")
        ai_gen.client.messages.create.side_effect = [tool_response_1, tool_response_2, text_response]

        tm, _ = _make_tool_manager()
        ai_gen.generate_response(query="multi-part question", tools=tm.get_tool_definitions(), tool_manager=tm)

        # Third API call (index 2) should have 5 messages in the chain
        final_messages = ai_gen.client.messages.create.call_args_list[2].kwargs["messages"]
        assert len(final_messages) == 5
        assert final_messages[0]["role"] == "user"           # original query
        assert final_messages[1]["role"] == "assistant"       # first tool_use
        assert final_messages[2]["role"] == "user"            # first tool_result
        assert final_messages[2]["content"][0]["type"] == "tool_result"
        assert final_messages[3]["role"] == "assistant"       # second tool_use
        assert final_messages[4]["role"] == "user"            # second tool_result
        assert final_messages[4]["content"][0]["type"] == "tool_result"

    def test_system_prompt_allows_two_searches(self):
        """System prompt no longer limits to one search."""
        assert "One search per query maximum" not in AIGenerator.SYSTEM_PROMPT
        assert "two searches" in AIGenerator.SYSTEM_PROMPT.lower()
