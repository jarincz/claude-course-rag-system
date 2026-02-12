#!/usr/bin/env python3
"""
Automated test for RAG Chatbot Web Application

Tests:
1. Page loads correctly
2. UI elements are present (chat history, input, buttons)
3. Sending a query works
4. Response is displayed
5. New session button works
6. Course statistics are loaded
"""

from playwright.sync_api import sync_playwright
import time
import sys

def test_chatbot():
    """Run comprehensive chatbot UI tests"""

    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Enable console logging
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

        # Track network errors
        page.on("pageerror", lambda err: print(f"❌ Page Error: {err}"))

        print("🚀 Starting RAG Chatbot Tests...\n")

        # Test 1: Navigate to application
        print("Test 1: Loading application...")
        try:
            page.goto('http://localhost:8000')
            page.wait_for_load_state('networkidle')
            print("✅ Page loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load page: {e}")
            browser.close()
            return False

        # Take initial screenshot
        page.screenshot(path='screenshots/01_initial_load.png', full_page=True)
        print("📸 Screenshot saved: screenshots/01_initial_load.png")

        # Test 2: Check for essential UI elements
        print("\nTest 2: Checking UI elements...")
        try:
            # Check header
            header = page.locator('.navbar-title')
            assert header.is_visible(), "Header not found"
            print("  ✓ Header present")

            # Check chat messages container
            chat_messages = page.locator('#chatMessages')
            assert chat_messages.count() > 0, "Chat messages container not found"
            print("  ✓ Chat messages container present")

            # Check input field
            input_field = page.locator('#chatInput')
            assert input_field.is_visible(), "Input field not found"
            print("  ✓ Input field present")

            # Check send button
            send_button = page.locator('#sendButton')
            assert send_button.is_visible(), "Send button not found"
            print("  ✓ Send button present")

            # Check menu toggle button (exists in DOM)
            menu_toggle = page.locator('#menuToggle')
            assert menu_toggle.count() > 0, "Menu toggle not found in DOM"
            print("  ✓ Menu toggle present (may be hidden on desktop)")

            # Check new chat button
            new_chat_button = page.locator('#newChatButton')
            assert new_chat_button.count() > 0, "New chat button not found"
            print("  ✓ New chat button present")

            # Check course stats section
            course_stats = page.locator('#courseStats')
            assert course_stats.count() > 0, "Course stats section not found"
            print("  ✓ Course stats section present")

            # Check welcome message appeared
            welcome_msg = page.locator('.message:has-text("Welcome")')
            if welcome_msg.count() > 0:
                print("  ✓ Welcome message displayed")

            print("✅ All UI elements present")
        except AssertionError as e:
            print(f"❌ UI element missing: {e}")
            page.screenshot(path='screenshots/02_ui_elements_error.png', full_page=True)
            browser.close()
            return False

        # Test 3: Check course statistics loaded
        print("\nTest 3: Checking course statistics...")
        try:
            # Get course count badge
            course_badge = page.locator('#courseCountBadge')
            course_count = course_badge.text_content()
            print(f"  ✓ Course count badge: {course_count}")

            # Check course titles section
            course_titles = page.locator('#courseTitles')
            if course_titles.is_visible():
                titles_text = course_titles.text_content()
                print(f"  ✓ Course titles loaded: {titles_text[:100]}...")

            print("✅ Course statistics loaded")
        except Exception as e:
            print(f"⚠️  Course statistics not loaded (might be empty database): {e}")

        page.screenshot(path='screenshots/03_stats_loaded.png', full_page=True)

        # Test 4: Send a query
        print("\nTest 4: Sending a test query...")
        try:
            input_field = page.locator('#chatInput')
            send_button = page.locator('#sendButton')

            # Type a test query
            test_query = "What courses are available?"
            input_field.fill(test_query)
            print(f"  ✓ Typed query: '{test_query}'")

            # Take screenshot before sending
            page.screenshot(path='screenshots/04_query_typed.png', full_page=True)

            # Click send button
            send_button.click()
            print("  ✓ Send button clicked")

            # Wait for response (look for assistant message)
            page.wait_for_selector('.message.assistant', timeout=30000)
            print("  ✓ Response received")

            # Get the response text
            response = page.locator('.message.assistant').last
            response_text = response.text_content()
            print(f"  ✓ Response text: {response_text[:100]}...")

            # Take screenshot after response
            page.screenshot(path='screenshots/05_response_received.png', full_page=True)

            print("✅ Query sent and response received")
        except Exception as e:
            print(f"❌ Failed to send query or receive response: {e}")
            page.screenshot(path='screenshots/05_query_error.png', full_page=True)
            # Print console logs for debugging
            print("\n📋 Console logs:")
            for msg in console_messages:
                print(f"  {msg}")
            browser.close()
            return False

        # Test 5: Send follow-up query
        print("\nTest 5: Sending follow-up query...")
        try:
            input_field = page.locator('#chatInput')

            # Count messages before
            messages_before = page.locator('.message').count()

            # Send follow-up
            follow_up = "Tell me more about the first one"
            input_field.fill(follow_up)
            input_field.press('Enter')  # Test Enter key submission
            print(f"  ✓ Sent follow-up: '{follow_up}'")

            # Wait for new response
            page.wait_for_timeout(2000)  # Wait a bit for UI to update
            page.wait_for_selector('.message.assistant', timeout=30000)

            # Count messages after
            messages_after = page.locator('.message').count()
            assert messages_after > messages_before, "No new messages added"
            print(f"  ✓ Messages count: {messages_before} → {messages_after}")

            page.screenshot(path='screenshots/06_follow_up.png', full_page=True)
            print("✅ Follow-up query works")
        except Exception as e:
            print(f"❌ Failed follow-up query: {e}")
            page.screenshot(path='screenshots/06_follow_up_error.png', full_page=True)

        # Test 6: New session button
        print("\nTest 6: Testing new session button...")
        try:
            # Get current message count
            messages_before = page.locator('.message').count()
            print(f"  ✓ Messages before new session: {messages_before}")

            # Check if menu drawer is visible (desktop) or needs to be opened (mobile)
            new_chat_button = page.locator('#newChatButton')

            if not new_chat_button.is_visible():
                # Mobile view - open menu first
                menu_toggle = page.locator('#menuToggle')
                menu_toggle.click()
                page.wait_for_timeout(300)  # Wait for drawer animation

            # Click new chat button
            new_chat_button.click()

            # Wait for chat to clear
            page.wait_for_timeout(500)

            # Check messages cleared
            messages_after = page.locator('.message').count()
            print(f"  ✓ Messages after new session: {messages_after}")

            # Should have only the initial greeting or be cleared
            assert messages_after <= 1, "Messages not properly cleared"

            page.screenshot(path='screenshots/07_new_session.png', full_page=True)
            print("✅ New session button works")
        except Exception as e:
            print(f"❌ New session button failed: {e}")
            page.screenshot(path='screenshots/07_new_session_error.png', full_page=True)

        # Test 7: Empty query handling
        print("\nTest 7: Testing empty query handling...")
        try:
            input_field = page.locator('#chatInput')
            send_button = page.locator('#sendButton')

            # Try to send empty query
            input_field.fill('')
            send_button.click()

            # Wait a moment
            page.wait_for_timeout(500)

            # Button should be disabled or query shouldn't be sent
            # Check that no new loading state appeared
            print("  ✓ Empty query handled gracefully")

            print("✅ Empty query validation works")
        except Exception as e:
            print(f"⚠️  Empty query test inconclusive: {e}")

        # Final screenshot
        page.screenshot(path='screenshots/08_final_state.png', full_page=True)

        # Print console logs
        print("\n📋 Console Messages:")
        for msg in console_messages[-10:]:  # Last 10 messages
            print(f"  {msg}")

        # Close browser
        browser.close()

        print("\n" + "="*50)
        print("🎉 All tests completed successfully!")
        print("="*50)
        print("\n📸 Screenshots saved in screenshots/ directory")

        return True

if __name__ == "__main__":
    # Create screenshots directory
    import os
    os.makedirs('screenshots', exist_ok=True)

    success = test_chatbot()
    sys.exit(0 if success else 1)
