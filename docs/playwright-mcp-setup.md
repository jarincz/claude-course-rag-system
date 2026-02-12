# Playwright MCP Integration

This document describes the Playwright MCP (Model Context Protocol) server integration for automated browser testing of the RAG chatbot application.

## What is Playwright MCP?

Playwright MCP is a server that provides browser automation capabilities through the Model Context Protocol. It allows Claude Code to:

- **Navigate web pages** - Open and interact with the application at http://localhost:8000
- **Take screenshots** - Capture visual states of the UI
- **Execute actions** - Click buttons, fill forms, submit queries
- **Extract content** - Read text, verify responses, check UI states
- **Test workflows** - Automated end-to-end testing of user flows

## Configuration

The Playwright MCP server has been configured in your `.claude.json`:

```json
{
  "projects": {
    "/Users/jaroslavnemecek/WORK/Development/starting-ragchatbot-codebase-main": {
      "mcpServers": {
        "playwright": {
          "command": "npx",
          "args": [
            "-y",
            "@executeautomation/playwright-mcp-server"
          ]
        }
      }
    }
  }
}
```

This configuration:
- Uses `npx` to run the Playwright MCP server (no local installation needed)
- The `-y` flag automatically accepts prompts
- Uses the `@executeautomation/playwright-mcp-server` package

## Available Tools

Once activated, Playwright MCP provides the following tools:

### 1. `playwright_navigate`
Navigate to a URL in the browser.

**Parameters:**
- `url` (string): The URL to navigate to

**Example:**
```
Navigate to http://localhost:8000
```

### 2. `playwright_screenshot`
Take a screenshot of the current page or a specific element.

**Parameters:**
- `name` (string): Name for the screenshot file
- `selector` (string, optional): CSS selector for specific element
- `width` (number, optional): Viewport width
- `height` (number, optional): Viewport height

**Example:**
```
Take a screenshot of the chat interface
```

### 3. `playwright_click`
Click on an element.

**Parameters:**
- `selector` (string): CSS selector for the element to click

**Example:**
```
Click the "Send" button
```

### 4. `playwright_fill`
Fill in a form field.

**Parameters:**
- `selector` (string): CSS selector for the input field
- `value` (string): Value to fill in

**Example:**
```
Fill the query input with "What is lesson 1 about?"
```

### 5. `playwright_evaluate`
Execute JavaScript in the browser context.

**Parameters:**
- `script` (string): JavaScript code to execute

**Example:**
```
Get the current session ID from localStorage
```

### 6. `playwright_console`
View browser console logs.

**Example:**
```
Check for JavaScript errors in the console
```

## Usage Examples

### Test the Chat Interface

```
1. Navigate to http://localhost:8000
2. Take a screenshot to verify the page loaded
3. Fill the input field with "What topics does the course cover?"
4. Click the send button
5. Take a screenshot of the response
6. Verify the response appears in the chat
```

### Debug Frontend Issues

```
1. Navigate to http://localhost:8000
2. Check the browser console for errors
3. Take a screenshot of the current state
4. Execute JavaScript to inspect the DOM state
```

### Automated Testing Workflow

```
1. Start the backend server (uv run uvicorn backend.app:app --reload)
2. Navigate to http://localhost:8000
3. Test the following scenarios:
   - Send a query and verify response
   - Create a new session
   - Load course statistics
   - Test error handling
4. Capture screenshots for each step
5. Verify all functionality works as expected
```

## How to Activate

After adding the configuration, **restart Claude Code**:

1. Exit the current Claude Code session (Cmd+Q or type `/exit`)
2. Relaunch Claude Code
3. The Playwright MCP server will automatically start
4. Tools will be available in the conversation

## Troubleshooting

### MCP Server Not Loading

If the Playwright MCP server doesn't load:

1. **Check Node.js is installed:**
   ```bash
   node --version  # Should show v18 or higher
   ```

2. **Test the server manually:**
   ```bash
   npx -y @executeautomation/playwright-mcp-server
   ```

3. **Check Claude Code logs:**
   - Look for MCP-related errors in the console
   - Verify the project path matches your configuration

### Browser Not Launching

If the browser doesn't launch when using Playwright tools:

1. **Install Playwright browsers:**
   ```bash
   npx playwright install
   ```

2. **Check for errors:**
   ```bash
   npx playwright test --list
   ```

### Permissions Issues

If you get permission errors:

1. **Allow Claude Code to run Playwright tools:**
   - Claude Code will prompt for permission on first use
   - Add to `.claude/settings.local.json` if needed

## Integration with Testing

You can use Playwright MCP to create automated tests for the RAG chatbot:

### Example Test Scenario

```markdown
Test: Query Processing Flow

1. **Setup**
   - Start backend: `uv run uvicorn backend.app:app --reload --port 8000`
   - Navigate to: http://localhost:8000

2. **Test Steps**
   a. Verify UI loads correctly
   b. Enter query: "What is lesson 1 about?"
   c. Click send button
   d. Wait for response
   e. Verify response appears
   f. Check for sources section
   g. Verify session ID is created

3. **Expected Results**
   - Response appears within 5 seconds
   - Sources section shows relevant documents
   - Session ID is stored in localStorage
   - No console errors

4. **Cleanup**
   - Clear session
   - Close browser
```

## Best Practices

1. **Always start the backend first:**
   ```bash
   uv run uvicorn backend.app:app --reload --port 8000
   ```

2. **Use descriptive screenshot names:**
   ```
   playwright_screenshot("chat-interface-initial-load")
   playwright_screenshot("query-response-received")
   ```

3. **Wait for elements to load:**
   - Use selectors that wait for elements to appear
   - Check console logs for loading states

4. **Combine with manual testing:**
   - Use Playwright MCP for repetitive tests
   - Manually verify complex interactions

## Resources

- **Playwright MCP Repository:** https://github.com/executeautomation/playwright-mcp-server
- **Playwright Documentation:** https://playwright.dev
- **MCP Specification:** https://modelcontextprotocol.io

## Next Steps

Now that Playwright MCP is configured:

1. **Restart Claude Code** to activate the MCP server
2. **Test the integration** by asking Claude to navigate to the app
3. **Create test scenarios** for key user flows
4. **Document issues** found during automated testing
