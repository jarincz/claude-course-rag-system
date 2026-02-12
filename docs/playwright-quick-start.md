# Playwright MCP Quick Start

Quick reference for using Playwright MCP to test the RAG chatbot interface.

## Prerequisites

1. **Backend running:**
   ```bash
   uv run uvicorn backend.app:app --reload --port 8000
   ```

2. **Claude Code restarted** (to load Playwright MCP)

## Common Test Commands

### 1. Initial Page Load Test

**Ask Claude:**
```
Navigate to localhost:8000 and take a screenshot of the initial page
```

**What it does:**
- Opens the application in a browser
- Captures the initial UI state
- Verifies the page loads correctly

---

### 2. Send a Query Test

**Ask Claude:**
```
On localhost:8000:
1. Fill the input with "What is lesson 1 about?"
2. Click the send button
3. Take a screenshot after the response appears
```

**What it tests:**
- Input field functionality
- Send button interaction
- Response rendering
- UI state after query

---

### 3. Check Browser Console

**Ask Claude:**
```
Navigate to localhost:8000 and check the browser console for any errors
```

**What it does:**
- Opens developer console
- Captures JavaScript errors
- Shows network requests
- Helps debug frontend issues

---

### 4. Test New Session Flow

**Ask Claude:**
```
On localhost:8000:
1. Send a query
2. Click "New Session" button
3. Verify the chat history clears
4. Take screenshots before and after
```

**What it tests:**
- Session management
- UI state reset
- localStorage handling

---

### 5. Verify Course Stats

**Ask Claude:**
```
Navigate to localhost:8000 and verify the course statistics load in the sidebar
```

**What it tests:**
- API call to /api/courses
- Sidebar rendering
- Course count display

---

### 6. Full User Flow Test

**Ask Claude:**
```
Test the complete user flow on localhost:8000:
1. Take initial screenshot
2. Send query: "What topics does the course cover?"
3. Verify response appears with sources
4. Take screenshot of response
5. Click new session
6. Send another query: "Tell me about lesson 2"
7. Take final screenshot
8. Check console for errors
```

**What it tests:**
- End-to-end user experience
- Multiple query handling
- Session management
- Error-free operation

---

## Element Selectors

Common CSS selectors for the application:

```css
/* Input field */
#user-input

/* Send button */
button[type="submit"]  /* or specific button text */

/* Chat messages */
#chat-history .message

/* New session button */
button:contains("New Session")

/* Course stats */
.course-stats
```

---

## Debugging Tips

### Check Session Storage

**Ask Claude:**
```
Execute JavaScript on localhost:8000 to check localStorage for session_id
```

### Inspect Response Time

**Ask Claude:**
```
Navigate to localhost:8000, send a query, and measure the time until response appears
```

### Verify API Calls

**Ask Claude:**
```
Check the network tab for the POST request to /api/query
```

---

## Example Test Session

Here's a complete example conversation with Claude:

**You:** "Start the playwright test suite"

**Claude:** "I'll test the RAG chatbot interface. First, let me verify the backend is running..."

**You:** "The backend is running on port 8000"

**Claude:** "Great! Let me run through the tests..."

Then Claude will:
1. Navigate to localhost:8000
2. Take initial screenshot
3. Send test queries
4. Verify responses
5. Check console errors
6. Provide test summary

---

## Screenshots

Screenshots are saved with descriptive names:
- `initial-load.png` - First page load
- `query-sent.png` - After sending query
- `response-received.png` - After response appears
- `new-session.png` - After session reset

---

## Troubleshooting

### "Browser not found"
```bash
npx playwright install
```

### "Page timeout"
- Check backend is running
- Verify port 8000 is accessible
- Check for CORS issues

### "Element not found"
- Verify selector is correct
- Check if element loaded
- Add wait time if needed

---

## Next Steps

After basic tests work:

1. **Create test scenarios** for edge cases
2. **Automate regression testing** for new features
3. **Set up CI/CD** with Playwright tests
4. **Add visual regression** testing

See `playwright-mcp-setup.md` for detailed documentation.
