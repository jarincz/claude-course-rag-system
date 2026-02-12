// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, courseTitles, courseCountBadge, menuToggle, menuDrawer, menuOverlay;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    courseTitles = document.getElementById('courseTitles');
    courseCountBadge = document.getElementById('courseCountBadge');
    menuToggle = document.getElementById('menuToggle');
    menuDrawer = document.getElementById('menuDrawer');
    menuOverlay = document.getElementById('menuOverlay');

    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Menu toggle
    menuToggle.addEventListener('click', toggleMenu);
    menuOverlay.addEventListener('click', closeMenu);

    // Close menu on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeMenu();
    });

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
            closeMenu(); // Close menu after selecting a question
        });
    });

    // New Chat button
    const newChatButton = document.getElementById('newChatButton');
    if (newChatButton) {
        newChatButton.addEventListener('click', () => {
            createNewSession();
            closeMenu();
        });
    }

    // Collapsible sections
    document.querySelectorAll('.collapsible-header').forEach(header => {
        header.addEventListener('click', toggleSection);
    });
}

// Menu Functions
function toggleMenu() {
    menuDrawer.classList.toggle('open');
    menuOverlay.classList.toggle('visible');
}

function closeMenu() {
    menuDrawer.classList.remove('open');
    menuOverlay.classList.remove('visible');
}

function toggleSection(e) {
    const header = e.currentTarget;
    const section = header.getAttribute('data-section');
    const content = document.querySelector(`[data-content="${section}"]`);
    const isExpanded = header.getAttribute('aria-expanded') === 'true';

    // Toggle state
    header.setAttribute('aria-expanded', !isExpanded);
    content.classList.toggle('collapsed');
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        // Handle both object format and legacy string format
        const sourceItems = sources.map(source => {
            // Check if source is an object with text/link or just a string
            if (typeof source === 'object' && source.text) {
                // Source object format: {text: "...", link: "..."}
                if (source.link) {
                    // Clickable link (opens in new tab) with icon
                    return `<div class="source-item">
                        <svg class="source-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                            <polyline points="15 3 21 3 21 9"></polyline>
                            <line x1="10" y1="14" x2="21" y2="3"></line>
                        </svg>
                        <a href="${escapeHtml(source.link)}" target="_blank" rel="noopener noreferrer" class="source-link">${escapeHtml(source.text)}</a>
                    </div>`;
                } else {
                    // No link - plain text
                    return `<div class="source-item source-item-no-link">${escapeHtml(source.text)}</div>`;
                }
            } else {
                // Legacy string format (fallback)
                return `<div class="source-item source-item-no-link">${escapeHtml(source)}</div>`;
            }
        }).join('');

        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources (${sources.length})</summary>
                <div class="sources-content">${sourceItems}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');

        const data = await response.json();
        console.log('Course data received:', data);

        // Update course count badge in navbar
        if (courseCountBadge) {
            courseCountBadge.textContent = data.total_courses;
        }

        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<button class="course-title-item" data-course="${escapeHtml(title)}">${escapeHtml(title)}</button>`)
                    .join('');

                // Add click handlers to course items
                document.querySelectorAll('.course-title-item').forEach(button => {
                    button.addEventListener('click', (e) => {
                        const courseTitle = e.currentTarget.getAttribute('data-course');
                        chatInput.value = `What is covered in the "${courseTitle}" course?`;
                        sendMessage();
                        closeMenu();
                    });
                });
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }

    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (courseCountBadge) {
            courseCountBadge.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}