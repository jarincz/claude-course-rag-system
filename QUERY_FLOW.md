# User Query Flow - Course Materials RAG System

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Browser)                       │
│                      (frontend/script.js)                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    [User types question]
                              ↓
                    sendMessage() function
                              ↓
        ┌───────────────────────────────────┐
        │ 1. Capture user input             │
        │ 2. Show loading spinner           │
        │ 3. Disable input/button           │
        └───────────────────────────────────┘
                              ↓
        POST /api/query (JSON)
        {
            "query": "What is lesson 1 about?",
            "session_id": "current-session-id"
        }
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│                    (backend/app.py)                             │
│                  POST /api/query endpoint                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌───────────────────────────────────┐
        │ 1. Validate QueryRequest          │
        │    - Extract query & session_id   │
        │ 2. Create session if needed       │
        └───────────────────────────────────┘
                              ↓
        Call: rag_system.query(query, session_id)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              RAG System (backend/rag_system.py)                 │
│              RAGSystem.query() method                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌───────────────────────────────────┐
        │ Step 1: Get Conversation History  │
        │ (if session exists)               │
        └───────────────────────────────────┘
                              ↓
        session_manager.get_conversation_history(session_id)
                              ↓
        ┌───────────────────────────────────┐
        │ Step 2: Initialize AI Generator   │
        │ with query + context              │
        └───────────────────────────────────┘
                              ↓
        ┌───────────────────────────────────┐
        │ Step 3: Setup Search Tools        │
        │ (CourseSearchTool)                │
        └───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│          AI Generator (backend/ai_generator.py)                 │
│   AIGenerator.generate_response() with tools                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌───────────────────────────────────┐
        │ Call Claude API                   │
        │ - Model: claude-3-5-sonnet        │
        │ - Max tokens: 800                 │
        │ - Temperature: 0                  │
        │ - Tools: [search_course_content]  │
        │ - System prompt: education focus │
        └───────────────────────────────────┘
                              ↓
        [Claude decides if search needed]
                              ↓
        ┌──────────────────────────────────────┐
        │ If tool_use stop_reason:             │
        │ → Execute tool with Claude's inputs  │
        │ If direct answer:                    │
        │ → Return text response directly      │
        └──────────────────────────────────────┘
                              ↓
                    IF TOOL IS USED:
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│        Search Tools (backend/search_tools.py)                   │
│    ToolManager.execute_tool() →                                │
│    CourseSearchTool.execute()                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌───────────────────────────────────┐
        │ CourseSearchTool Parameters:      │
        │ - query: user's search term       │
        │ - course_name: optional filter    │
        │ - lesson_number: optional filter  │
        └───────────────────────────────────┘
                              ↓
        Call: vector_store.search()
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│      Vector Store (backend/vector_store.py)                     │
│    Semantic search using ChromaDB                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌───────────────────────────────────┐
        │ Step 1: Resolve course name       │
        │ (fuzzy matching if provided)      │
        └───────────────────────────────────┘
                              ↓
        ┌───────────────────────────────────┐
        │ Step 2: Build metadata filter     │
        │ (course_title, lesson_number)     │
        └───────────────────────────────────┘
                              ↓
        ┌───────────────────────────────────┐
        │ Step 3: Semantic search           │
        │ using embeddings (query)          │
        │ on course_content collection      │
        └───────────────────────────────────┘
                              ↓
        ChromaDB returns:
        {
            "documents": ["Lesson content..."],
            "metadata": [
                {
                    "course_title": "Course Name",
                    "lesson_number": 1,
                    "source": "file.pdf"
                }
            ]
        }
                              ↓
        ┌───────────────────────────────────┐
        │ Format results with context       │
        │ [Course Name - Lesson 1]          │
        │ Content...                        │
        └───────────────────────────────────┘
                              ↓
        Return formatted search results
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│      Back to AI Generator - Tool Results Processing             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌───────────────────────────────────┐
        │ 1. Add initial response to        │
        │    message history                │
        │ 2. Add tool results to history    │
        │ 3. Send to Claude for synthesis   │
        └───────────────────────────────────┘
                              ↓
        [Claude creates final answer based on search results]
                              ↓
        Return: Final generated answer (string)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│      Back to RAG System - Store Conversation                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        session_manager.add_message(session_id, user_query, answer)
                              ↓
        Return: (answer, sources_list)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│      Back to FastAPI - Build Response                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        QueryResponse {
            "answer": "The answer to your question...",
            "sources": ["Course Name - Lesson 1"],
            "session_id": "session-id"
        }
                              ↓
        HTTP 200 Response (JSON)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Browser)                           │
│                   (script.js - Fetch)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
        ┌───────────────────────────────────┐
        │ 1. Parse JSON response            │
        │ 2. Remove loading spinner         │
        │ 3. Update session_id if new       │
        │ 4. Add message to chat history    │
        │ 5. Show sources if available      │
        │ 6. Scroll to latest message       │
        │ 7. Re-enable input/button         │
        └───────────────────────────────────┘
                              ↓
        [Display answer in chat bubble]
        [Display collapsible sources list]
```

## Step-by-Step Code Walkthrough

### 1. FRONTEND: User Submits Query
**File:** `frontend/script.js:45-96`

```javascript
async function sendMessage() {
    // 1. Get query from input
    const query = chatInput.value.trim();

    // 2. Disable input and show loading
    chatInput.disabled = true;
    const loadingMessage = createLoadingMessage();

    // 3. Send POST request to backend
    const response = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query: query,
            session_id: currentSessionId  // null for first query
        })
    });

    // 4. Parse response
    const data = await response.json();
    currentSessionId = data.session_id;  // Save session ID

    // 5. Display answer with sources
    addMessage(data.answer, 'assistant', data.sources);
}
```

### 2. BACKEND: Receive and Route Query
**File:** `backend/app.py:56-74`

```python
@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    # 1. Extract query and session_id from request
    session_id = request.session_id

    # 2. Create new session if needed
    if not session_id:
        session_id = rag_system.session_manager.create_session()

    # 3. Process query using RAG system
    answer, sources = rag_system.query(request.query, session_id)

    # 4. Return response with sources
    return QueryResponse(
        answer=answer,
        sources=sources,
        session_id=session_id
    )
```

### 3. RAG SYSTEM: Query Processing with AI
**File:** `backend/rag_system.py:102-150`

```python
def query(self, query: str, session_id: Optional[str] = None) -> Tuple[str, List[str]]:
    # 1. Get conversation history for context
    history = self.session_manager.get_conversation_history(session_id)

    # 2. Setup search tools
    tool_manager = ToolManager()
    search_tool = CourseSearchTool(self.vector_store)
    tool_manager.register_tool(search_tool)

    # 3. Call AI generator with tools
    answer = self.ai_generator.generate_response(
        query=query,
        conversation_history=history,
        tools=tool_manager.get_tools_definitions(),
        tool_manager=tool_manager
    )

    # 4. Get sources from the last search
    sources = search_tool.last_sources if hasattr(search_tool, 'last_sources') else []

    # 5. Store in session history
    self.session_manager.add_message(session_id, query, answer)

    return answer, sources
```

### 4. AI GENERATOR: Claude API Call with Tools
**File:** `backend/ai_generator.py:43-135`

```python
def generate_response(self, query, conversation_history=None, tools=None, tool_manager=None):
    # 1. Build system prompt with instructions
    system_content = f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"

    # 2. Prepare Claude API call
    api_params = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 800,
        "temperature": 0,
        "messages": [{"role": "user", "content": query}],
        "system": system_content,
        "tools": tools,  # Include search tool definition
        "tool_choice": {"type": "auto"}  # Let Claude decide
    }

    # 3. Call Claude
    response = self.client.messages.create(**api_params)

    # 4. Check if Claude wants to use a tool
    if response.stop_reason == "tool_use" and tool_manager:
        # Handle tool execution
        return self._handle_tool_execution(response, api_params, tool_manager)
    else:
        # Direct response
        return response.content[0].text

def _handle_tool_execution(self, initial_response, base_params, tool_manager):
    # 1. Extract tool call from Claude's response
    for content_block in initial_response.content:
        if content_block.type == "tool_use":
            # 2. Execute the tool
            tool_result = tool_manager.execute_tool(
                content_block.name,
                **content_block.input  # Pass tool arguments
            )
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": content_block.id,
                "content": tool_result
            })

    # 3. Send tool results back to Claude
    # 4. Claude generates final answer based on search results
    final_response = self.client.messages.create(**final_params)
    return final_response.content[0].text
```

### 5. SEARCH TOOL: Vector Search
**File:** `backend/search_tools.py:52-86`

```python
def execute(self, query, course_name=None, lesson_number=None):
    # 1. Call vector store search
    results = self.store.search(
        query=query,
        course_name=course_name,
        lesson_number=lesson_number
    )

    # 2. Format results
    formatted = self._format_results(results)

    # 3. Store sources for UI
    self.last_sources = sources  # Save for UI display

    return formatted
```

### 6. VECTOR STORE: Semantic Search
**File:** `backend/vector_store.py:61-100`

```python
def search(self, query, course_name=None, lesson_number=None):
    # 1. Resolve course name if provided (fuzzy matching)
    course_title = self._resolve_course_name(course_name)

    # 2. Build metadata filter
    filter_dict = self._build_filter(course_title, lesson_number)

    # 3. Semantic search using embeddings
    # Query is converted to embeddings, then compared against stored documents
    results = self.course_content.query(
        query_texts=[query],
        where=filter_dict,
        n_results=self.max_results,
        include=["documents", "metadatas"]
    )

    # 4. Return SearchResults object with documents and metadata
    return SearchResults(
        documents=results["documents"][0],
        metadata=results["metadatas"][0],
        error=None
    )
```

## Key Components Explained

### Request/Response Models
**File:** `backend/app.py:38-52`

```python
class QueryRequest(BaseModel):
    query: str              # User's question
    session_id: Optional[str] = None  # Session for context

class QueryResponse(BaseModel):
    answer: str             # AI-generated answer
    sources: List[str]      # Source documents
    session_id: str         # Session ID for continuation
```

### Tool Definition (What Claude Sees)
```json
{
    "name": "search_course_content",
    "description": "Search course materials...",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "..."},
            "course_name": {"type": "string", "description": "..."},
            "lesson_number": {"type": "integer", "description": "..."}
        },
        "required": ["query"]
    }
}
```

### Session Management
- **First query**: No `session_id` → Backend creates new session
- **Subsequent queries**: Include `session_id` → Backend retrieves conversation history
- **History context**: Passed to Claude for multi-turn conversations

## Flow Summary

1. **Frontend** → Sends user query + session_id
2. **FastAPI** → Routes to `/api/query` endpoint
3. **RAG System** → Orchestrates the process
4. **AI Generator** → Calls Claude with search tools available
5. **Claude** → Decides if search is needed
6. **Search Tool** → Executes semantic search if needed
7. **Vector Store** → Returns relevant documents
8. **Claude** → Generates final answer
9. **FastAPI** → Returns answer + sources
10. **Frontend** → Displays answer with sources

## Error Handling

- Frontend catches fetch errors and displays error messages
- Backend wraps RAG calls in try-catch
- Vector store returns empty `SearchResults` if nothing found
- Claude's response is always a string (never fails)
