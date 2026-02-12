import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **Up to two searches per query** for complex queries requiring comparisons or multi-part questions
- For simple single-topic questions, one search is sufficient
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    MAX_TOOL_ROUNDS = 2  # Maximum sequential tool-call rounds per query

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager, round: int = 1):
        """
        Handle execution of tool calls and get follow-up response.
        Supports up to MAX_TOOL_ROUNDS sequential rounds of tool calling.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters (includes "tools" and "system")
            tool_manager: Manager to execute tools
            round: Current tool-call round number (1-based)

        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()

        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})

        # Execute all tool calls and collect results
        tool_results = []
        tool_error = False
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )
                except Exception as e:
                    tool_result = f"Tool execution error: {str(e)}"
                    tool_error = True

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })

        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Include tools if under max rounds and no execution error
        include_tools = (round < self.MAX_TOOL_ROUNDS) and not tool_error

        # Prepare follow-up API call
        followup_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        if include_tools and "tools" in base_params:
            followup_params["tools"] = base_params["tools"]
            followup_params["tool_choice"] = {"type": "auto"}

        # Get follow-up response
        followup_response = self.client.messages.create(**followup_params)

        # If Claude wants another tool call and we can still recurse
        if followup_response.stop_reason == "tool_use" and include_tools:
            updated_params = {**base_params, "messages": messages}
            return self._handle_tool_execution(followup_response, updated_params, tool_manager, round=round + 1)

        # Extract text from the final response
        for block in followup_response.content:
            if hasattr(block, 'text'):
                return block.text

        return "I was unable to generate a complete response. Please try rephrasing your question."