# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Course Materials RAG System** - A full-stack Retrieval-Augmented Generation (RAG) application that answers questions about course materials using semantic search and Claude AI.

- **Type**: Web application (FastAPI backend + vanilla JS frontend)
- **Language**: Python 3.13+ (backend), JavaScript (frontend)
- **Key Tech**: ChromaDB (vector DB), Anthropic Claude, FastAPI, Sentence Transformers

## Architecture & Data Flow

### System Architecture

The application has three main layers:

```
FRONTEND (JavaScript)
  └─→ FastAPI Backend (Python)
        └─→ RAG System (Orchestration)
              ├─→ AI Generator (Claude API + Tool Use)
              ├─→ Vector Store (ChromaDB with embeddings)
              ├─→ Session Manager (Conversation history)
              └─→ Search Tools (Semantic search interface)
```

### Critical Query Processing Flow

When a user submits a query:

1. **Frontend** sends POST to `/api/query` with `{query, session_id}`
2. **FastAPI** receives request, creates session if needed
3. **RAGSystem.query()** orchestrates:
   - Retrieves conversation history (session context)
   - Sets up search tools and tool definitions
   - Calls Claude with tools via `AIGenerator.generate_response()`
4. **Claude decides**: Does this query need semantic search?
   - **YES**: Executes `search_course_content` tool → VectorStore searches ChromaDB
   - **NO**: Answers directly from knowledge + context
5. **VectorStore.search()** performs:
   - Fuzzy course name resolution (if provided)
   - Metadata filtering (course_title, lesson_number)
   - Semantic search using embeddings on `course_content` collection
6. **Claude synthesizes** search results with conversation context
7. **Frontend** receives `{answer, sources, session_id}` and displays

See `QUERY_FLOW.md` for detailed flow diagram and step-by-step walkthrough.

## Backend Structure

### Module Organization

```
backend/
├── app.py                    # FastAPI application & HTTP endpoints
├── rag_system.py             # RAG orchestrator (main logic)
├── ai_generator.py           # Claude API integration with tool use
├── vector_store.py           # ChromaDB wrapper with semantic search
├── search_tools.py           # Tool definitions & ToolManager
├── session_manager.py        # Conversation history storage
├── document_processor.py      # Course document parsing
├── models.py                 # Pydantic data models
└── config.py                 # Configuration & environment variables
```

### Key Classes & Responsibilities

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| **RAGSystem** | Orchestrates entire flow | `query()`, `add_course_folder()`, `get_course_analytics()` |
| **AIGenerator** | Claude API calls with tool use | `generate_response()`, `_handle_tool_execution()` |
| **VectorStore** | ChromaDB operations & semantic search | `search()`, `add_course_content()`, `_resolve_course_name()` |
| **ToolManager** | Manages available tools for Claude | `register_tool()`, `execute_tool()`, `get_tools_definitions()` |
| **CourseSearchTool** | Implements search_course_content tool | `execute()`, `_format_results()` |
| **SessionManager** | Tracks conversation history per session | `create_session()`, `get_conversation_history()`, `add_message()` |

### Important Implementation Details

**Tool-Based Architecture**:
- Claude uses the `search_course_content` tool when needed (tool_choice: "auto")
- Tool definition in `search_tools.py:CourseSearchTool.get_tool_definition()`
- Claude passes parameters: `query`, `course_name` (optional), `lesson_number` (optional)

**Vector Search**:
- Two ChromaDB collections: `course_catalog` (metadata), `course_content` (searchable text)
- Embeddings: `all-MiniLM-L6-v2` (sentence-transformers)
- Chunk size: 800 characters with 100 char overlap (config.py)
- Max results: 5 documents per search

**Session Context**:
- `SessionManager.MAX_HISTORY = 2` conversations remembered
- History formatted as: "User: {query}\nAssistant: {answer}\n..."
- Passed to Claude for multi-turn conversation awareness

**Import Pattern** (Fixed):
- All backend imports are **relative** (`.models`, `.config`, etc.)
- When called as module from `app.py`: `from .rag_system import RAGSystem`

## Frontend Structure

```
frontend/
├── index.html      # Single-page chat interface
├── script.js       # Event handlers & API communication
└── style.css       # Styling (no frameworks)
```

### Frontend Key Functions

- `sendMessage()` - Captures user input, sends POST to `/api/query`, displays response
- `addMessage()` - Appends message to chat history with markdown rendering
- `createNewSession()` - Resets chat (clears `currentSessionId`)
- `loadCourseStats()` - Fetches `/api/courses` for sidebar stats

## Development Commands

### Setup & Installation

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Create .env file (required)
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

### Running the Application

```bash
# Development with auto-reload (from root)
uv run uvicorn backend.app:app --reload --port 8000

# Or use the shell script
chmod +x run.sh
./run.sh

# The app runs on http://localhost:8000
# API docs available at http://localhost:8000/docs (Swagger UI)
```

### Loading Course Materials

Currently, the `RAGSystem` has methods to load course documents but they're not exposed via API:

```python
# In Python shell or separate script:
from backend.rag_system import RAGSystem
from backend.config import config

rag = RAGSystem(config)
courses_added, chunks_created = rag.add_course_folder("path/to/courses", clear_existing=True)
print(f"Added {courses_added} courses with {chunks_created} chunks")
```

Supported formats: `.pdf`, `.docx`, `.txt`

## Configuration

### Environment Variables

Create `.env` file (copy from `.env.example`):

```
ANTHROPIC_API_KEY=sk-ant-...  # Required: Anthropic API key
```

### Configurable Parameters

**File**: `backend/config.py`

- `ANTHROPIC_MODEL`: Claude model to use (default: "claude-sonnet-4-20250514")
- `CHUNK_SIZE`: Document chunk size for vector storage (800)
- `CHUNK_OVERLAP`: Overlap between chunks (100)
- `MAX_RESULTS`: Search results per query (5)
- `MAX_HISTORY`: Conversation turns to remember (2)
- `EMBEDDING_MODEL`: Sentence transformer model ("all-MiniLM-L6-v2")
- `CHROMA_PATH`: ChromaDB storage location ("./chroma_db")

## Data Models

**Core Pydantic Models** (backend/models.py):

- `Lesson`: lesson_number, title, lesson_link
- `Course`: title (unique ID), course_link, instructor, lessons[]
- `CourseChunk`: content, course_title, lesson_number, chunk_index

**API Request/Response** (backend/app.py):

- `QueryRequest`: query, session_id (optional)
- `QueryResponse`: answer, sources, session_id
- `CourseStats`: total_courses, course_titles

## Common Development Tasks

### Debugging Query Flow

1. Check Claude's system prompt in `ai_generator.py:SYSTEM_PROMPT`
2. Verify tool definition matches expected parameters in `search_tools.py`
3. Check ChromaDB collections exist: `vector_store.py:_create_collection()`
4. Inspect search results formatting: `search_tools.py:_format_results()`
5. API logs at `/docs` endpoint (Swagger UI shows request/response)

### Adding New Search Parameters

1. Update tool definition in `CourseSearchTool.get_tool_definition()` (schema)
2. Add parameter to `execute()` method signature
3. Pass to `vector_store.search()`
4. Handle in `VectorStore._build_filter()` for ChromaDB where clause

### Modifying AI Behavior

1. Change system prompt in `AIGenerator.SYSTEM_PROMPT`
2. Adjust temperature/max_tokens in `ai_generator.py:base_params`
3. Tool choice strategy in `generate_response()` ("auto" vs "required" vs specific tool)

### Extending with New Tools

1. Create class inheriting from `Tool` (ABC in search_tools.py)
2. Implement `get_tool_definition()` and `execute()` methods
3. Register in `RAGSystem.query()`: `tool_manager.register_tool(new_tool)`
4. Claude will automatically see it and decide to use when appropriate

## Important Constraints & Gotchas

### Import Fixes Applied

- All relative imports in backend modules use dot notation (`.config`, `.models`)
- Running `uv run uvicorn backend.app:app` requires relative imports
- If imports fail, check that imports are relative (not `from config import ...`)

### Vector Store Behavior

- **First query creates collections**: Check `chroma_db` folder after first query
- **Course names are case-sensitive** in storage but fuzzy-matched at search time
- **Lesson numbers must be integers**: Document parser extracts from "Lesson N" patterns
- **Empty search results**: Returns clear message, doesn't fall back to alternative searches

### Session Management

- Sessions are ephemeral (stored in memory in `SessionManager`)
- No persistence between application restarts
- Max 2 conversation turns remembered (configured in `config.py`)
- Each new tab/browser gets new session

### Claude Tool Behavior

- Temperature 0 (deterministic) - change in `ai_generator.py` if needed
- Max 800 tokens per response - adjust in `base_params`
- One search per query maximum (enforced in system prompt)
- If search returns nothing, Claude still answers based on knowledge

## Deployment Considerations

- **Frontend**: Static HTML/JS served by FastAPI (no build step)
- **Database**: ChromaDB persists to `./chroma_db` directory (needs to exist on target)
- **Secrets**: `ANTHROPIC_API_KEY` required as environment variable
- **Performance**: Embeddings computed on first search (takes ~2-3s), cached afterward
- **Dependencies**: All in `pyproject.toml` and `uv.lock` (includes heavy packages like torch)

## Testing & Debugging

### Manual API Testing

Use Swagger UI at `http://localhost:8000/docs` to:
- Test `/api/query` endpoint directly
- View request/response schema
- See errors with full tracebacks

### Browser Console

Frontend logs to browser console:
- Course stats loading: `console.log('Loading course stats...')`
- Error messages: `console.error()`

### Python REPL Testing

```bash
uv run python
>>> from backend.rag_system import RAGSystem
>>> from backend.config import config
>>> rag = RAGSystem(config)
>>> answer, sources = rag.query("What is lesson 1 about?", session_id=None)
>>> print(answer)
```

### Automated Browser Testing (Playwright MCP)

This project is configured with Playwright MCP for automated frontend testing.

**Available after Claude Code restart:**
- Navigate to pages and take screenshots
- Click buttons and fill forms
- Execute JavaScript in browser context
- View console logs and debug issues
- Test complete user workflows

**Example test workflow:**
```
1. Start backend: uv run uvicorn backend.app:app --reload --port 8000
2. Ask Claude: "Navigate to localhost:8000 and test the chat interface"
3. Claude will use Playwright tools to interact with the UI
4. Screenshots and console logs available for debugging
```

See `docs/playwright-mcp-setup.md` for complete documentation and usage examples.

## Files Created by the System

- `.env` - Environment variables (not in git)
- `chroma_db/` - Vector database (generated, not in git)
- `.venv/` - Virtual environment (not in git)

These are in `.gitignore` and safe to delete (will be recreated as needed).
