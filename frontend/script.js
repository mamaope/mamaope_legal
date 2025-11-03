// Modern JavaScript for mamaope_legal AI - Inspired by Glass Health and OpenEvidence
const API_URL = '/api/v1';
let chatHistory = [];
let accessToken = null;
let currentUser = null;
let isAuthenticated = false;
let currentSession = null;
let currentTheme = 'light';

// Initialize the application (robust to late script injection)
function bootApp() {
    // Check if markdown libraries are loaded
    console.log('🚀 [App] Initializing mamaope_legal AI');
    console.log('📚 [Libraries] marked.js loaded:', typeof marked !== 'undefined');
    if (typeof marked !== 'undefined') {
        console.log('📚 [Libraries] marked.js version:', marked.version || 'unknown');
    }
    console.log('🧼 [Libraries] DOMPurify loaded:', typeof DOMPurify !== 'undefined');
    if (typeof DOMPurify !== 'undefined') {
        console.log('🧼 [Libraries] DOMPurify version:', DOMPurify.version || 'unknown');
    }

    initializeTheme();
    initializeApp();
    setupEventListeners();
    checkAuthentication();
    updateSendButton();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootApp);
} else {
    // DOM is already ready; run immediately
    bootApp();
}

function updateAuthenticationUI(authenticated) {
    const landingPage = document.getElementById('landingPage');
    const chatContainer = document.querySelector('.chat-container');
    const appContainer = document.getElementById('appContainer');
    const sidebar = document.getElementById('sidebar');
    const headerActions = document.querySelector('.header-actions');
    const headerUserProfile = document.getElementById('headerUserProfile');
    const sampleSection = document.querySelector('.sample-questions');
    const disclaimerSection = document.querySelector('.disclaimer-section');
    const chatMessages = document.getElementById('landingChatMessages');

    if (authenticated) {
        if (sidebar) sidebar.style.display = 'flex';
        if (appContainer) appContainer.classList.add('authenticated');
        if (headerActions) headerActions.style.display = 'none';
        if (headerUserProfile) headerUserProfile.style.display = 'flex';
        if (landingPage) landingPage.style.display = 'flex';
        if (sampleSection) sampleSection.style.display = 'none';
        if (disclaimerSection) disclaimerSection.style.display = 'none';
        if (chatContainer) chatContainer.classList.remove('centered');
        if (chatMessages) {
            const welcome = chatMessages.querySelector('.welcome-message');
            if (welcome) welcome.remove();
            chatMessages.style.justifyContent = 'flex-start';
            chatMessages.style.paddingTop = 'var(--spacing-md)';
        }
        updateUserInfo();
        updateHeaderUserInfo();
        loadUserSessions();
    } else {
        if (sidebar) sidebar.style.display = 'none';
        if (headerActions) headerActions.style.display = 'flex';
        if (headerUserProfile) headerUserProfile.style.display = 'none';
        if (appContainer) appContainer.classList.remove('authenticated');
        if (landingPage) landingPage.style.display = 'flex';
        if (sampleSection) sampleSection.style.display = '';
        if (disclaimerSection) disclaimerSection.style.display = '';
        if (chatContainer) chatContainer.classList.add('centered');
        clearChat();
    }
}

function initializeApp() {
    // Set up message input auto-resize for landing page
    const landingMessageInput = document.getElementById('landingMessageInput');
    const landingSendButton = document.getElementById('landingSendButton');
    
    // Landing page input
    if (landingMessageInput) {
        // Ensure textarea does not block clicks
        landingMessageInput.style.pointerEvents = 'auto';
        landingMessageInput.addEventListener('input', function() {
            autoResizeTextarea.call(this);
            updateCharCounter();
            updateSendButton();
        });
        // Simple keydown handler - matches working example
        landingMessageInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault(); // Stop newline
                sendMessage();
            }
        });
        landingMessageInput.addEventListener('keyup', () => {
            updateSendButton();
        });
        landingMessageInput.addEventListener('change', () => {
            updateSendButton();
        });
        landingMessageInput.addEventListener('focus', () => {
            const charCounter = document.getElementById('charCounter');
            if (charCounter) charCounter.style.display = 'block';
        });
    }
    
    // Initially disable send button
    if (landingSendButton) {
        // Ensure button is clickable even if overlapping elements exist
        landingSendButton.style.pointerEvents = 'auto';
        landingSendButton.style.position = 'relative';
        landingSendButton.style.zIndex = '2';
        landingSendButton.disabled = true;
        landingSendButton.setAttribute('disabled', 'true');
        landingSendButton.setAttribute('aria-disabled', 'true');

        // Explicit click listener to guarantee click handling
        landingSendButton.addEventListener('click', (e) => {
            console.log('🖱️ [UI] Landing send button clicked');
            e.preventDefault();
            // Defensive: if enabled by content, proceed
            const input = document.getElementById('landingMessageInput');
            if (input && input.value && input.value.trim().length > 0) {
                sendMessage();
            } else {
                // Sync state if mismatch
                updateSendButton();
            }
        });
    }
    
    // Set up chat expansion observer
    setupChatExpansionObserver();
}

function updateCharCounter() {
    const messageInput = document.getElementById('landingMessageInput');
    const charCounter = document.getElementById('charCounter');
    if (!messageInput || !charCounter) return;

    const value = messageInput.value || '';
    const length = value.length;
    const maxLength = 2000;
    
    charCounter.textContent = `${length} / ${maxLength}`;
    
    // Update styling based on length
    charCounter.classList.remove('warning', 'error');
    if (length > maxLength * 0.9) {
        charCounter.classList.add('warning');
    }
    if (length > maxLength) {
        charCounter.classList.add('error');
    }
}

function updateSendButton() {
    const messageInput = document.getElementById('landingMessageInput');
    const sendButton = document.getElementById('landingSendButton');
    if (!messageInput || !sendButton) return;

    const value = messageInput.value || '';
    const hasText = value.trim().length > 0;
    const notTooLong = value.length <= 2000;

    const enabled = hasText && notTooLong;
    setSendButtonEnabled(enabled);
}

function setSendButtonEnabled(enabled) {
    const sendButton = document.getElementById('landingSendButton');
    if (!sendButton) return;
    sendButton.disabled = !enabled;
    if (enabled) {
        sendButton.removeAttribute('disabled');
        sendButton.setAttribute('aria-disabled', 'false');
    } else {
        sendButton.setAttribute('disabled', 'true');
        sendButton.setAttribute('aria-disabled', 'true');
    }
}

function setupEventListeners() {
    console.log('🔧 [Setup] Setting up event listeners...');
    
    // Auth form submission
    const authForm = document.getElementById('authForm');
    console.log('🔧 [Setup] Auth form found:', !!authForm);
    if (authForm) {
        authForm.addEventListener('submit', handleAuthSubmit);
        console.log('✅ [Setup] Auth form submit listener added');
    } else {
        console.error('❌ [Setup] Auth form NOT found!');
    }
    
    // Modal close on outside click
    const modal = document.getElementById('authModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeAuthModal();
            }
        });
    }
}

function setupChatExpansionObserver() {
    const chatMessages = document.getElementById('landingChatMessages');
    const chatContainer = document.querySelector('.chat-container');
    if (!chatMessages || !chatContainer) return;
    
    // Initially center the chat
    chatContainer.classList.add('centered');
    
    // Expand chat area when messages are added
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Check if welcome message was removed
                const welcomeMessage = chatMessages.querySelector('.welcome-message');
                if (!welcomeMessage) {
                    chatContainer.classList.remove('centered');
                    chatMessages.style.justifyContent = 'flex-start';
                    chatMessages.style.paddingTop = 'var(--spacing-md)';
                }
            }
        });
    });
    
    observer.observe(chatMessages, { childList: true, subtree: true });
}

function checkAuthentication() {
    // Check for stored token
    const storedToken = localStorage.getItem('accessToken');
    const storedUser = localStorage.getItem('currentUser');
    console.log('🔐 [AuthBoot] accessToken present:', !!storedToken, 'currentUser present:', !!storedUser);

    if (storedToken) {
        accessToken = storedToken;
        // If we have a stored user, try to parse and validate expiry
        if (storedUser) {
            try {
                const userData = JSON.parse(storedUser);
                if (isTokenExpired(userData)) {
                    console.log('🔐 [AuthBoot] Token expired, clearing stored auth');
                    clearStoredAuth();
                    updateAuthenticationUI(false);
                    return;
                }
                currentUser = userData;
            } catch (err) {
                console.warn('🔐 [AuthBoot] Failed to parse currentUser; proceeding with token only');
            }
        }

        isAuthenticated = true;
        // Immediately show authenticated UI on the basis of token presence
        updateAuthenticationUI(true);
        // Validate with backend and hydrate user if needed
        validateTokenWithBackend(storedToken, currentUser || null);
    } else {
        console.log('🔐 [AuthBoot] No token found; showing unauthenticated UI');
        updateAuthenticationUI(false);
    }
}

function isTokenExpired(userData) {
    // Check if user data has expiration info
    if (userData && userData.exp) {
        const expirationTime = userData.exp * 1000; // Convert to milliseconds
        const currentTime = Date.now();

        // If token expires in the next 5 minutes, consider it expired
        return (expirationTime - currentTime) < (5 * 60 * 1000);
    }

    // If no expiration info, assume it's valid (backward compatibility)
    return false;
}

async function validateTokenWithBackend(token, userData) {
    try {
        const response = await fetch(`${API_URL}/auth/me`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            }
        });

        if (response.ok) {
            // Backend reachable; try to parse and honor explicit invalidation only
            try {
                const data = await response.json();
                if (data && data.success) {
                    console.log('Token validation successful');
                    return;
                } else {
                    console.warn('Token validation returned non-success payload; keeping UI authenticated unless unauthorized');
                    return;
                }
            } catch (e) {
                console.warn('Failed to parse /auth/me response; keeping UI authenticated');
                return;
            }
        } else {
            // Only clear auth on explicit unauthorized
            if (response.status === 401 || response.status === 403) {
                console.log('Token unauthorized, clearing auth');
                clearStoredAuth();
                updateAuthenticationUI(false);
            } else {
                console.warn(`Non-OK status from /auth/me (${response.status}); keeping UI authenticated`);
            }
        }
    } catch (error) {
        console.error('Token validation error:', error);
        // Don't clear auth on network errors, just log
    }
}

function updateUserInfo() {
    if (currentUser) {
        const userName = document.getElementById('userName');
        const userEmail = document.getElementById('userEmail');
        
        if (userName) userName.textContent = currentUser.full_name || currentUser.username;
        if (userEmail) userEmail.textContent = currentUser.email;
    }
}

// Authentication Modal Functions
function showAuthModal(mode) {
    const modal = document.getElementById('authModal');
    const modalTitle = document.getElementById('modalTitle');
    const submitBtn = document.getElementById('submitBtn');
    const confirmPasswordGroup = document.getElementById('confirmPasswordGroup');
    const fullNameGroup = document.getElementById('fullNameGroup');
    const modalFooterText = document.getElementById('modalFooterText');
    
    if (mode === 'login') {
        modalTitle.textContent = 'Sign In';
        submitBtn.textContent = 'Sign In';
        confirmPasswordGroup.style.display = 'none';
        fullNameGroup.style.display = 'none';
        modalFooterText.innerHTML = 'Don\'t have an account? <a href="#" onclick="toggleAuthMode()">Sign up</a>';
    } else {
        modalTitle.textContent = 'Create Account';
        submitBtn.textContent = 'Sign Up';
        confirmPasswordGroup.style.display = 'block';
        fullNameGroup.style.display = 'block';
        modalFooterText.innerHTML = 'Already have an account? <a href="#" onclick="toggleAuthMode()">Sign in</a>';
    }
    
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    
    // CRITICAL FIX: Attach event listener NOW (after modal is shown)
    console.log('🔓 [Modal] Attaching submit listener...');
    const authForm = document.getElementById('authForm');
    if (authForm) {
        // Remove any old listeners by cloning
        const newForm = authForm.cloneNode(true);
        authForm.parentNode.replaceChild(newForm, authForm);
        
        // Attach fresh listener
        newForm.addEventListener('submit', handleAuthSubmit);
        console.log('✅ [Modal] Submit listener attached!');
            } else {
        console.error('❌ [Modal] Auth form not found!');
    }
    
    // Focus first input
    setTimeout(() => {
        const firstInput = document.getElementById('authModal').querySelector('input');
        if (firstInput) firstInput.focus();
    }, 100);
}

function closeAuthModal() {
    const modal = document.getElementById('authModal');
    modal.classList.remove('show');
    document.body.style.overflow = '';
    
    // Clear form
    const form = document.getElementById('authForm');
    if (form) form.reset();
}

function toggleAuthMode() {
    const modalTitle = document.getElementById('modalTitle');
    const isLogin = modalTitle.textContent === 'Sign In';
    showAuthModal(isLogin ? 'register' : 'login');
}

async function handleAuthSubmit(event) {
    console.log('🚀 [Auth] Form submitted!');
        event.preventDefault();
    console.log('🚀 [Auth] Event prevented');
    
    const formData = new FormData(event.target);
    console.log('🚀 [Auth] Form data:', Object.fromEntries(formData));
    const email = formData.get('email');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirmPassword');
    const fullName = formData.get('fullName');
    
    const submitBtn = document.getElementById('submitBtn');
    const isLogin = submitBtn.textContent === 'Sign In';
    
    // Client-side validation
    if (!email || !password) {
        showAuthError('Email and password are required');
            return;
        }
        
    if (!isLogin) {
        if (!fullName) {
            showAuthError('Full name is required');
            return;
        }
        if (password !== confirmPassword) {
            showAuthError('Passwords do not match');
            return;
        }
        if (password.length < 8) {
            showAuthError('Password must be at least 8 characters long');
            return;
        }
        const strongPwd = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;
        if (!strongPwd.test(password)) {
            showAuthError('Password must include uppercase, lowercase, number, and special character');
            return;
        }
    }
    
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.textContent = isLogin ? 'Signing In...' : 'Creating Account...';
    
    try {
        if (isLogin) {
            await loginUser(email, password);
        } else {
            await registerUser(fullName, email, password);
        }
    } catch (error) {
        console.error('❌ [Login] Auth error:', error);
        console.error('❌ [Login] Error stack:', error.stack);
        showAuthError(error.message || 'An error occurred. Please try again.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = isLogin ? 'Sign In' : 'Sign Up';
    }
}

async function loginUser(email, password) {
    console.log('🔐 [Login] Attempting login for:', email);
    console.log('🔐 [Login] API URL:', `${API_URL}/auth/login`);
    
    const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({ email, password })
    });
    
    console.log('🔐 [Login] Response status:', response.status);
    const data = await response.json();
    console.log('🔐 [Login] Response data:', data);
    
    if (data.success) {
        accessToken = data.data.access_token;
        currentUser = data.data.user;
        isAuthenticated = true;
        
        // Store in localStorage
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        
        // Update UI
        updateAuthenticationUI(true);
        closeAuthModal();
        
        // Show welcome message
        addMessage(`Welcome back, ${currentUser.full_name || currentUser.username}! How can I help you today?`, [], 'ai', false);
    } else {
        const errorMessage = data.metadata?.errors?.join(', ') || data.data?.message || 'Login failed';
        throw new Error(errorMessage);
    }
}

async function registerUser(fullName, email, password) {
    // Parse full name into first and last name
    const nameParts = fullName.trim().split(' ');
    const firstName = nameParts[0] || '';
    const lastName = nameParts.slice(1).join(' ') || '';
    
    const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({
            first_name: firstName,
            last_name: lastName,
            email: email,
            password: password
        })
            });
            
    const data = await response.json();
                
    if (response.ok && data.success) {
        // Registration successful, switch to login
        showAuthError('Registration successful! Please sign in with your credentials.', 'success');
                setTimeout(() => {
            showAuthModal('login');
                }, 2000);
        } else {
        let message = '';
        if (data && typeof data === 'object') {
            if (data.metadata && Array.isArray(data.metadata.errors) && data.metadata.errors.length) {
                message = data.metadata.errors.join(', ');
            }
            if (!message && data.data && typeof data.data.message === 'string') {
                message = data.data.message;
            }
            if (!message && typeof data.message === 'string') {
                message = data.message;
            }
            if (!message && data.detail) {
                if (Array.isArray(data.detail)) {
                    message = data.detail.map(d => d.msg || d.message || (typeof d === 'string' ? d : '')).filter(Boolean).join(', ');
                } else if (typeof data.detail === 'string') {
                    message = data.detail;
                }
            }
        }
        if (!message) {
            message = 'Registration failed: please check your input and try again';
        }
        throw new Error(message);
    }
}

function showAuthError(message, type = 'error') {
    // Remove existing error messages
    const existingError = document.querySelector('.auth-error');
    if (existingError) existingError.remove();
    
    // Create new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = `auth-error ${type}`;
    errorDiv.textContent = message;
    errorDiv.style.color = type === 'success' ? '#059669' : '#dc2626';
    errorDiv.style.fontSize = '0.875rem';
    errorDiv.style.marginTop = '0.5rem';
    
    // Insert after form
    const form = document.getElementById('authForm');
    form.parentNode.insertBefore(errorDiv, form.nextSibling);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 5000);
}

function logout() {
    accessToken = null;
    currentUser = null;
    isAuthenticated = false;
    currentSession = null;
    
    // Clear localStorage
    clearStoredAuth();
    
    // Update UI
    updateAuthenticationUI(false);
    
    // Show signup prompt
    showAuthModal('login');
}

function clearStoredAuth() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('currentUser');
}

// Header User Menu Functions
function updateHeaderUserInfo() {
    if (!currentUser) return;
    
    const headerUserName = document.getElementById('headerUserName');
    const headerUserRole = document.getElementById('headerUserRole');
    const dropdownUserName = document.getElementById('dropdownUserName');
    const dropdownUserEmail = document.getElementById('dropdownUserEmail');
    
    const fullName = currentUser.full_name || currentUser.username || 'User';
    const email = currentUser.email || 'user@example.com';
    const role = currentUser.role || 'Legal Professional';
    
    if (headerUserName) headerUserName.textContent = fullName;
    if (headerUserRole) headerUserRole.textContent = role;
    if (dropdownUserName) dropdownUserName.textContent = fullName;
    if (dropdownUserEmail) dropdownUserEmail.textContent = email;
}

function toggleUserMenu() {
    const userDropdownMenu = document.getElementById('userDropdownMenu');
    const headerUserButton = document.querySelector('.header-user-button');
    
    if (!userDropdownMenu) return;
    
    const isOpen = userDropdownMenu.style.display === 'block';
    
    if (isOpen) {
        userDropdownMenu.style.display = 'none';
        if (headerUserButton) {
            headerUserButton.setAttribute('aria-expanded', 'false');
        }
            } else {
        userDropdownMenu.style.display = 'block';
        if (headerUserButton) {
            headerUserButton.setAttribute('aria-expanded', 'true');
        }
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const userMenu = document.querySelector('.header-user-menu');
    const userDropdownMenu = document.getElementById('userDropdownMenu');
    
    if (userMenu && userDropdownMenu && !userMenu.contains(event.target)) {
        userDropdownMenu.style.display = 'none';
        const headerUserButton = document.querySelector('.header-user-button');
        if (headerUserButton) {
            headerUserButton.setAttribute('aria-expanded', 'false');
        }
    }
});

// Menu item functions
function showProfile() {
    console.log('Show Profile clicked');
    toggleUserMenu();
    // TODO: Implement profile page
    alert('Profile page coming soon!');
}

function showSettings() {
    console.log('Show Settings clicked');
    toggleUserMenu();
    // TODO: Implement settings page
    alert('Settings page coming soon!');
}

function showHelp() {
    console.log('Show Help clicked');
    toggleUserMenu();
    // TODO: Implement help page
    alert('Help & Support coming soon!');
}

// Make functions globally accessible
window.toggleUserMenu = toggleUserMenu;
window.showProfile = showProfile;
window.showSettings = showSettings;
window.showHelp = showHelp;

// Message Functions
async function sendMessage() {
    // Get the input and button
    const messageInput = document.getElementById('landingMessageInput');
    const sendButton = document.getElementById('landingSendButton');
    
    if (!messageInput) {
        console.error('No message input found');
        return;
    }
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    console.log('🚀 [Frontend] sendMessage called');
    console.log('   Message:', message);
    console.log('   Authenticated:', isAuthenticated);
    console.log('   Access token:', accessToken ? 'Present' : 'Missing');
    
    // Check authentication
    if (!isAuthenticated) {
        console.log('🔐 [Frontend] Not authenticated, showing auth modal');
        showAuthModal('login');
            return;
        }
        
    // Disable input and show loading
        messageInput.disabled = true;
        setSendButtonEnabled(false);
        sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    // Show loading indicator
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'flex';
    }
        
        // Add user message to chat
    addMessage(message, [], 'user', true);
    messageInput.value = '';
    autoResizeTextarea.call(messageInput);
    
    try {
        // Create or get current session
        if (!currentSession) {
            console.log('📝 [Frontend] Creating new session');
            currentSession = await createSession();
            if (currentSession) {
                // Refresh the sessions list to show the new session
                loadUserSessions();
            }
        }
        
        console.log('🔵 [Frontend] Sending legal consultation request');
        console.log('   Session ID:', currentSession?.id);
        console.log('   Chat history:', formatChatHistory());
        
        // Send message to API
        const response = await fetch(`${API_URL}/consult/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({
                case_data: message,
                chat_history: formatChatHistory(),
                session_id: currentSession ? currentSession.id : null
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        console.log('🔵 [Frontend] Legal consultation response received:', data);
        
        // Check if response has the expected structure
        if (!data.data) {
            throw new Error('Invalid response structure: missing data field');
        }
        
        // Add AI response to chat
        const aiResponseContent = data.data.model_response;
        const aiResponseSources = []; 
        const aiResponseStatus = 'ai'; 
        addMessage(aiResponseContent, aiResponseSources, aiResponseStatus, false);

        // Update chat history
        chatHistory.push({
            user: message,
            ai: aiResponseContent
        });
        if (data.data.session_id && (!currentSession || !currentSession.id)) {
            console.log(`📝 [Frontend] Session established with ID: ${data.data.session_id}`);
            currentSession = { id: data.data.session_id };
        }
        
        } catch (error) {
            console.error('Error:', error);
            addMessage(`Sorry, there was an error processing your request: ${error.message}`, [], 'error', false);
        } finally {
            // Hide loading indicator
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
        
            // Re-enable input
            messageInput.disabled = false;
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
            updateSendButton();
            messageInput.focus();
        }
    }

function addMessage(content, sources = [], status = 'ai', isUser = false) { 
    
    const messageContent = String(content || "An internal error occurred. Please check server logs."); 
    const messageType = isUser ? 'user' : (status === 'error' ? 'error' : 'ai'); 
    const hasSources = (sources && Array.isArray(sources) && sources.length > 0);
    
    console.log('💬 [Frontend] addMessage called:', { type: messageType, hasSources: hasSources });
    console.log('📄 [Frontend] FULL RAW CONTENT:\n' + messageContent);
    console.log('📊 [Frontend] Content length:', messageContent.length); 
    console.log('🔍 [Frontend] Has ## headings:', messageContent.includes('##'));
    console.log('🔍 [Frontend] Has blank lines:', messageContent.includes('\n\n'));
    
    const chatMessages = document.getElementById('landingChatMessages');
    
    if (!chatMessages) {
        console.error('No chat messages container found');
        return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${messageType}-message`;
    
    if (messageType === 'user') {
        messageDiv.innerHTML = `
            <div class="message-content">
            ${formatUserMessage(messageContent)}
            </div>
        `;
    } else if (messageType === 'ai') {
        let sourceHtml = '';
        if (hasSources) {
             sourceHtml = `
                 <div class="message-sources">
                     <strong>Sources:</strong> 
                     ${sources.join(', ')}
                 </div>
             `;
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">
            ${formatAIResponse(messageContent)}
            </div>
            ${sourceHtml}
        `;
    } else if (messageType === 'error') {
        messageDiv.innerHTML = `
            <div class="message-content">
                <strong>⚠️ Error:</strong><br>
                ${messageContent}
            </div>
        `;
    }
    
    chatMessages.appendChild(messageDiv);
    
    // Smooth scroll
    setTimeout(() => {
        messageDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
    
    // Remove welcome message after first interaction
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
}

function formatUserMessage(message) {
    return message.replace(/\n/g, '<br>');
}

// ===== HTML ENTITY DECODER =====
function decodeHTMLEntities(text) {
    const textarea = document.createElement('textarea');
    textarea.innerHTML = text;
    return textarea.value;
}

// ===== MARKDOWN FIXER - Add missing blank lines =====
function fixMarkdownSpacing(markdown) {
    console.log('🔧 [Markdown] Fixing spacing...');
    console.log('🔍 [Markdown] Input has newlines:', markdown.includes('\n'));
    console.log('🔍 [Markdown] Input has blank lines:', markdown.includes('\n\n'));
    
    let fixed = markdown;
    
    // CRITICAL: Strip closing ## from headings (## Heading ## → ## Heading)
    // marked.js expects open headings, not closed ones
    // Use backreference \1 to ensure start and end markers MATCH
    // ## Text ## ✓  |  ### Text ### ✓  |  ## Text ### ✗
    fixed = fixed.replace(/(#{1,6})\s+([\s\S]+?)\s+\1\s*$/gm, '$1 $2');
    console.log('✂️ [Markdown] Removed closing ## from headings (matched pairs only)');
    
    // STEP 1: If there are NO newlines at all (everything on one line), add newlines before ## headings
    if (!markdown.includes('\n')) {
        console.log('⚠️ [Markdown] Text is all on ONE LINE - adding line breaks');
        
        // First, add line breaks before each ## heading
        fixed = fixed.replace(/\s+(##\s)/g, '\n\n$1');
        
        // Then, add line breaks after common heading patterns
        // Match specific heading titles and add newline after them
        const headingTitles = [
            "Legal Analysis",
            "Statutory Interpretation",
            "Relevant Jurisprudence",
            "Applicable Legislation",
            "Summary of Facts",
            "Client Rights and Obligations",
            "Procedural Requirements",
            "Conclusion and Next Steps"
        ];
        
        headingTitles.forEach(title => {
            // Match: ## emoji Title - Content -> ## emoji Title\n\n- Content
            // Also match: ## emoji Title Content -> ## emoji Title\n\nContent
            const escapedTitle = title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            
            // First, match heading followed by " - " (dash with spaces for subheadings)
            const dashPattern = new RegExp(`(##\\s+[^\\s]+\\s+${escapedTitle})\\s+-\\s+`, 'g');
            fixed = fixed.replace(dashPattern, '$1\n\n- ');
            
            // Then, match heading followed by [ or ( (for citations or parentheses)
            const bracketPattern = new RegExp(`(##\\s+[^\\s]+\\s+${escapedTitle})\\s+(\\[|\\()`, 'g');
            fixed = fixed.replace(bracketPattern, '$1\n\n$2');
            
            // Then, match heading followed by capital letter, number, or lowercase letter (any content)
            const pattern = new RegExp(`(##\\s+[^\\s]+\\s+${escapedTitle})\\s+([A-Za-z0-9])`, 'g');
            fixed = fixed.replace(pattern, '$1\n\n$2');
            
            // Also match heading followed by > (blockquote)
            const blockquotePattern = new RegExp(`(##\\s+[^\\s]+\\s+${escapedTitle})\\s+(>)`, 'g');
            fixed = fixed.replace(blockquotePattern, '$1\n\n$2');
        });
        
        // Add line breaks between numbered list items
        // Match: 1. **Title** (XX%): Long text with citations [source]. 2. **Next** -> line break before 2.
        fixed = fixed.replace(/(\]\.\s+)(\d+\.\s+\*\*)/g, '$1\n\n$2');
        // Also match sentences ending with period followed by number
        fixed = fixed.replace(/([a-z]\.\s+)(\d+\.\s+\*\*)/g, '$1\n\n$2');
        // Match: ). 2. **Next** (closing parenthesis followed by number)
        fixed = fixed.replace(/(\)\.\s+)(\d+\.\s+\*\*)/g, '$1\n\n$2');
        
        // Add line breaks between bullet list items  
        // Match: - **Item**: Text. - **Next** -> line break before -
        fixed = fixed.replace(/(\]\.\s+)([-*]\s+\*\*)/g, '$1\n$2');
        fixed = fixed.replace(/([a-z]\.\s+)([-*]\s+\*\*)/g, '$1\n$2');
        
        // Handle bullet points without bold (like red flags)
        // Match: ]. - Next item -> ].\n- Next item
        fixed = fixed.replace(/(\]\.\s+)([-*]\s+[A-Z])/g, '$1\n$2');
        // Match: word. - Next item -> word.\n- Next item
        fixed = fixed.replace(/([a-z]\.\s+)([-*]\s+[A-Z])/g, '$1\n$2');
        // Match: ). - Next item -> ).\n- Next item
        fixed = fixed.replace(/(\)\.\s+)([-*]\s+[A-Z])/g, '$1\n$2');
    }
    
    // STEP 2: Add blank lines before ANY heading (##, ###, ####, etc.)
    fixed = fixed.replace(/([^\n])\n(#{1,6}\s)/g, '$1\n\n$2');
    
    // STEP 3: Add blank lines BETWEEN consecutive headings (any level)
    // Handles: ## Title ##\n### Subtitle ### (no blank line between)
    fixed = fixed.replace(/(#{1,6}\s[^\n]+)\n(#{1,6}\s)/g, '$1\n\n$2');
    
    // STEP 4: Add blank line after heading if followed by content (not another heading)
    // SKIP THIS STEP - Already handled by stripping closing ## at the top
    // The heading closure regex handles this correctly
    // This regex was BREAKING multi-word headings like "## Anatomic Abnormalities ##"
    // Then handle headings with single newline
    fixed = fixed.replace(/(#{1,6}[^\n]+)\n([^#\n])/g, '$1\n\n$2');
    
    // STEP 5: Add blank lines before numbered lists
    fixed = fixed.replace(/([^\n])\n(\d+\.\s)/g, '$1\n\n$2');
    // Also ensure blank line before first list item after ANY heading
    fixed = fixed.replace(/(#{1,6}[^\n]+)\n(\d+\.\s)/g, '$1\n\n$2');
    
    // STEP 6: Add blank lines before bullet lists
    fixed = fixed.replace(/([^\n])\n([-*]\s)/g, '$1\n\n$2');
    
    // STEP 7: Add blank line after lists (before non-list content)
    fixed = fixed.replace(/(\n(?:\d+\.|-|\*)\s[^\n]+)\n([^\n\d\-\*#])/g, '$1\n\n$2');
    
    // STEP 8: Add blank lines before blockquotes
    fixed = fixed.replace(/([^\n>])\n(>\s)/g, '$1\n\n$2');
    
    // STEP 9: Add blank lines after blockquotes
    fixed = fixed.replace(/(>\s[^\n]+)\n([^>\n#])/g, '$1\n\n$2');
    
    // STEP 10: Clean up any triple+ blank lines
    fixed = fixed.replace(/\n{3,}/g, '\n\n');
    
    // STEP 11: Remove blank lines at the very start
    fixed = fixed.replace(/^\n+/, '');
    
    console.log('✅ [Markdown] Spacing fixed');
    console.log('🔍 [Markdown] Now has blank lines:', fixed.includes('\n\n'));
    
    if (fixed.includes('\n\n')) {
        const blankLineCount = (fixed.match(/\n\n/g) || []).length;
        console.log('📊 [Markdown] Added', blankLineCount, 'blank line sections');
    }
    
    return fixed;
}

// ===== ENHANCED MARKDOWN RENDERER =====
function renderMarkdownWithEnhancements(markdown) {
    console.log('📝 [Markdown] Rendering with marked.js');
    console.log('📥 [Markdown] Input preview:', markdown.substring(0, 150) + '...');
    
    // Check if marked is available
    if (typeof marked === 'undefined') {
        console.error('❌ [Markdown] marked.js is not loaded! Returning plain text.');
        return markdown.replace(/\n/g, '<br>');
    }
    
    // Check if DOMPurify is available
    if (typeof DOMPurify === 'undefined') {
        console.error('❌ [Markdown] DOMPurify is not loaded! Using marked without sanitization.');
    }
    
    // Decode HTML entities first (e.g., &quot; to ", &#x27; to ', &amp; to &)
    const decodedMarkdown = decodeHTMLEntities(markdown);
    console.log('🔓 [Markdown] Decoded preview:', decodedMarkdown.substring(0, 150) + '...');
    
    // Fix markdown spacing (add blank lines between elements)
    let fixedMarkdown = fixMarkdownSpacing(decodedMarkdown);
    
    // Fix emoji on separate line from heading text (e.g., "## 🏥\nClinical Overview" -> "## 🏥 Clinical Overview")
    fixedMarkdown = fixedMarkdown.replace(/(##\s*[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}])\s*\n\s*([A-Z])/gu, '$1 $2');
    
    // Convert **BOLD HEADINGS** to proper markdown headings (for old prompt format)
    // Match patterns like: **CLINICAL OVERVIEW** or **DIFFERENTIAL DIAGNOSES**
    const sectionHeadings = [
        'CLINICAL OVERVIEW',
        'Explanation',
        'Question',
        'Drug Interactions',
        'Drug-Drug Interaction',
        'Rationale',
        'Impression',
        'Conclusion',
        'Management Considerations',
        'Important Considerations',
        'Clinical Considerations',
        'Further Management',
        'Summary',
        'Differential Diagnosis',
        'Management',
        'References',
        'Investigations / Workup',
        'DIFFERENTIAL DIAGNOSES',
        'IMMEDIATE WORKUP & INVESTIGATIONS',
        'IMMEDIATE WORKUP &amp; INVESTIGATIONS',
        'MANAGEMENT & RECOMMENDATIONS',
        'MANAGEMENT &amp; RECOMMENDATIONS',
        'RED FLAGS / DANGER SIGNS',
        'RED FLAGS \\/ DANGER SIGNS',
        'ADDITIONAL INFORMATION NEEDED',
        'SOURCES'
    ];
    
    sectionHeadings.forEach(heading => {
        const escapedHeading = heading.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        // Match: **HEADING** anywhere (with optional whitespace before/after)
        const pattern = new RegExp(`\\*\\*${escapedHeading}\\*\\*`, 'gi');
        // Convert to title case: first letter of each word capitalized, rest lowercase
        const titleCase = heading.toLowerCase().replace(/\b\w/g, l => l.toUpperCase());
        fixedMarkdown = fixedMarkdown.replace(pattern, `\n\n## ${titleCase}\n\n`);
    });
    
    // Clean up multiple consecutive blank lines (more than 2)
    fixedMarkdown = fixedMarkdown.replace(/\n{3,}/g, '\n\n');
    
    // Remove blank lines at the very start
    fixedMarkdown = fixedMarkdown.replace(/^\n+/, '');
    
    console.log('🔧 [Markdown] Fixed preview:', fixedMarkdown.substring(0, 150) + '...');
    
    // Configure marked.js for better formatting
    marked.setOptions({
        breaks: false,       // Don't convert single \n to <br> (we need blank lines for lists)
        gfm: true,          // GitHub Flavored Markdown
        headerIds: false,    // Don't add IDs to headers
        mangle: false,      // Don't escape autolinked emails
        pedantic: false,    // Don't be overly strict
        sanitize: false,    // We'll use DOMPurify for this
        smartLists: true,   // Use smarter list behavior
        smartypants: true   // Use smart quotes
    });
    
    // Customize renderer for medical context
    const renderer = new marked.Renderer();
    
    // Enhanced heading renderer with medical icons
    renderer.heading = function(text, level) {
        // Check if text already has an emoji at the start (common pattern from AI)
        const emojiRegex = /^[\u{1F300}-\u{1F9FF}]|^[\u{2600}-\u{26FF}]/u;
        const hasEmoji = emojiRegex.test(text.trim());
        
        // If heading already has emoji, don't add another one
        if (hasEmoji) {
            const isAlert = text.toLowerCase().includes('alert') || text.toLowerCase().includes('red flag');
            const className = isAlert ? ' class="alert-heading"' : '';
            return `<h${level}${className}>${text}</h${level}>`;
        }
        
        // Otherwise, add icon based on content
        const iconMap = {
            'question': '📋',
            'rationale': '🧠',
            'impression': '💡',
            'clinical impression': '💡',
            'management': '⚕️',
            'further management': '⚕️',
            'sources': '📚',
            'knowledge base': '📚',
            'alert': '🚨',
            'clinical overview': '🏥',
            'differential diagnos': '🔍',  // Matches "diagnoses" or "diagnosis"
            'immediate workup': '🔬',
            'workup': '🔬',
            'red flags': '🚩',
            'treatment': '💊',
            'medication': '💊',
            'history': '📊',
            'examination': '🔬',
            'investigation': '🔬',
            'assessment': '📋',
            'plan': '📝',
            'follow-up': '📅',
            'prognosis': '📈'
        };
        
        // Find matching icon
        let icon = '';
        const lowerText = text.toLowerCase();
        for (const [key, value] of Object.entries(iconMap)) {
            if (lowerText.includes(key)) {
                icon = value + ' ';
                break;
            }
        }
        
        // Add appropriate styling for alert headings
        const isAlert = lowerText.includes('alert') || lowerText.includes('red flag');
        const className = isAlert ? ' class="alert-heading"' : '';
        
        return `<h${level}${className}>${icon}${text}</h${level}>`;
    };
    
    // Enhanced list renderer with better styling
    renderer.list = function(body, ordered, start) {
        const type = ordered ? 'ol' : 'ul';
        const startAttr = (ordered && start !== 1) ? ` start="${start}"` : '';
        const className = ordered ? ' class="ordered-list"' : ' class="unordered-list"';
        return `<${type}${className}${startAttr}>\n${body}</${type}>\n`;
    };
    
    // Enhanced list item renderer
    renderer.listitem = function(text) {
        // Detect if list item has emphasis or strong at the start
        const hasLeadingEmphasis = text.trim().startsWith('<strong>') || text.trim().startsWith('<em>');
        const className = hasLeadingEmphasis ? ' class="emphasized-item"' : '';
        return `<li${className}>${text}</li>\n`;
    };
    
    // Enhanced code block renderer
    renderer.code = function(code, language) {
        const validLanguage = language || 'plaintext';
        const escapedCode = code
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
        
        return `<div class="code-block-wrapper">
            <div class="code-block-header">
                <span class="code-language">${validLanguage}</span>
                <button class="copy-code-btn" onclick="copyCodeToClipboard(this)" title="Copy code">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
            <pre class="code-block"><code class="language-${validLanguage}">${escapedCode}</code></pre>
        </div>`;
    };
    
    // Enhanced inline code renderer
    renderer.codespan = function(code) {
        return `<code class="inline-code">${code}</code>`;
    };
    
    // Enhanced blockquote renderer
    renderer.blockquote = function(quote) {
        // Check if it's a note, warning, or tip
        const lowerQuote = quote.toLowerCase();
        let className = 'blockquote';
        let icon = '💬';
        
        if (lowerQuote.includes('note:') || lowerQuote.includes('📝')) {
            className += ' note';
            icon = '📝';
        } else if (lowerQuote.includes('warning:') || lowerQuote.includes('⚠️')) {
            className += ' warning';
            icon = '⚠️';
        } else if (lowerQuote.includes('tip:') || lowerQuote.includes('💡')) {
            className += ' tip';
            icon = '💡';
        } else if (lowerQuote.includes('important:') || lowerQuote.includes('❗')) {
            className += ' important';
            icon = '❗';
        }
        
        return `<blockquote class="${className}">
            <div class="blockquote-icon">${icon}</div>
            <div class="blockquote-content">${quote}</div>
        </blockquote>`;F
    };
    
    // Enhanced table renderer
    renderer.table = function(header, body) {
        return `<div class="table-wrapper">
            <table class="medical-table">
                <thead>${header}</thead>
                <tbody>${body}</tbody>
            </table>
        </div>`;
    };
    
    // Enhanced link renderer (open external links in new tab)
    renderer.link = function(href, title, text) {
        const isExternal = href.startsWith('http://') || href.startsWith('https://');
        const target = isExternal ? ' target="_blank" rel="noopener noreferrer"' : '';
        const titleAttr = title ? ` title="${title}"` : '';
        const icon = isExternal ? ' <i class="fas fa-external-link-alt"></i>' : '';
        return `<a href="${href}"${titleAttr}${target}>${text}${icon}</a>`;
    };
    
    // Set custom renderer
    marked.use({ renderer });
    
    // Pre-process fixed markdown for medical-specific enhancements
    let processedMarkdown = fixedMarkdown;
    
    // Highlight percentages (e.g., "85%")
    processedMarkdown = processedMarkdown.replace(/(\d+(?:\.\d+)?%)/g, '<span class="probability-badge">$1</span>');
    
    // Highlight medical ranges (e.g., "120/80 mmHg")
    processedMarkdown = processedMarkdown.replace(/(\d+\/\d+\s*(?:mmHg|mg\/dL|g\/dL|mEq\/L))/g, '<span class="medical-value">$1</span>');
    
    // Highlight temperature (e.g., "38.5°C" or "101.3°F")
    processedMarkdown = processedMarkdown.replace(/(\d+(?:\.\d+)?°[CF])/g, '<span class="medical-value">$1</span>');
    
    // Parse markdown to HTML
    let html = marked.parse(processedMarkdown);
    console.log('📤 [Markdown] Parsed HTML preview:', html.substring(0, 200) + '...');
    
    // Sanitize HTML with DOMPurify (prevent XSS)
    const cleanHtml = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(html, {
        ALLOWED_TAGS: [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'br', 'hr',
            'strong', 'em', 'u', 's', 'sub', 'sup',
            'ul', 'ol', 'li',
            'blockquote',
            'code', 'pre',
            'a',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'div', 'span',
            'i', 'button'
        ],
        ALLOWED_ATTR: [
            'class', 'id', 'style',
            'href', 'title', 'target', 'rel',
            'start',
            'onclick'
        ],
        ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i
    }) : html;
    
    console.log('✅ [Markdown] Rendering complete');
    return cleanHtml;
}

// Helper function to copy code to clipboard
function copyCodeToClipboard(button) {
    const codeBlock = button.closest('.code-block-wrapper').querySelector('code');
    const code = codeBlock.textContent;
    
    navigator.clipboard.writeText(code).then(() => {
        // Visual feedback
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i>';
        button.classList.add('copied');
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy code:', err);
    });
}

function formatAIResponse(response) {
    console.log('🎨 [Frontend] Formatting AI response:', response.substring(0, 200) + '...');
    console.log('📚 [Markdown] marked available:', typeof marked !== 'undefined');
    console.log('🧼 [Markdown] DOMPurify available:', typeof DOMPurify !== 'undefined');
    console.log('📄 [Markdown] Response contains markdown?', response.includes('##') || response.includes('**') || response.includes('- '));
    
    // Check if it's a JSON response (new format)
    if (response.trim().startsWith('{') && response.trim().endsWith('}')) {
        console.log('📦 [Format] Detected JSON response');
        return formatJSONResponse(response);
    }
    
    // Check if it's a differential diagnosis response
    if (response.includes('**DIFFERENTIAL DIAGNOSIS**')) {
        console.log('🔍 [Format] Detected differential diagnosis response');
        return formatDifferentialDiagnosis(response);
    }
    
    // Use enhanced markdown renderer if marked.js is available
    if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
        console.log('✅ [Markdown] Using enhanced markdown renderer');
        const rendered = renderMarkdownWithEnhancements(response);
        console.log('📤 [Markdown] Rendered HTML preview:', rendered.substring(0, 300) + '...');
        return rendered;
    }
    
    console.log('⚠️ [Markdown] Falling back to basic formatter');
    
    // Fallback to basic markdown formatting
    let formattedResponse = response;
    
    // Remove any existing HTML tags that might be in the response
    formattedResponse = formattedResponse.replace(/<[^>]*>/g, '');
    
    // Format headers (## and ###)
    formattedResponse = formattedResponse
        .replace(/^### (.*$)/gm, '<h4>$1</h4>')
        .replace(/^## (.*$)/gm, '<h3>$1</h3>')
        .replace(/^# (.*$)/gm, '<h2>$1</h2>');
    
    // Format bold text (**text** or __text__)
    formattedResponse = formattedResponse
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.*?)__/g, '<strong>$1</strong>');
    
    // Format italic text (*text* or _text_)
    formattedResponse = formattedResponse
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/_(.*?)_/g, '<em>$1</em>');
    
    // Format code blocks (```code```)
    formattedResponse = formattedResponse
        .replace(/```([\s\S]*?)```/g, '<pre class="code-block"><code>$1</code></pre>');
    
    // Format inline code (`code`)
    formattedResponse = formattedResponse
        .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    
    // Format links [text](url)
    formattedResponse = formattedResponse
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    
    // Format medical sections with icons
    formattedResponse = formattedResponse
        .replace(/\*\*Question:\*\*/g, '<h4>📋 Question:</h4>')
        .replace(/\*\*Rationale:\*\*/g, '<h4>🧠 Rationale:</h4>')
        .replace(/\*\*Impression:\*\*/g, '<h4>💡 Clinical Impression:</h4>')
        .replace(/\*\*Further Management:\*\*/g, '<h4>⚕️ Further Management:</h4>')
        .replace(/\*\*Sources:\*\*/g, '<h4>📚 Knowledge Base Sources:</h4>')
        .replace(/\*\*ALERT:\*\*/g, '<h4 style="color: #dc3545;">🚨 ALERT:</h4>')
        .replace(/\*\*Clinical Overview:\*\*/g, '<h4>🏥 Clinical Overview:</h4>')
        .replace(/\*\*Summary\*\*/g, '<h4>🏥 Summary</h4>')
        .replace(/\*\*References:\*\*/g, '<h4>📚 References:</h4>')
        .replace(/\*\*Correct Answer:\*\*/g, '<h4>💡 Correct Answer:</h4>')
        .replace(/\*\*Explanation:\*\*/g, '<h4>🧠 Explanation:</h4>')
        .replace(/\*\*Differential Diagnosis:\*\*/g, '<h4>🔍 Differential Diagnosis:</h4>')
        .replace(/\*\*Immediate Workup:\*\*/g, '<h4>🔬 Immediate Workup:</h4>')
        .replace(/\*\*Investigations \/ Workup:\*\*/g, '<h4>🔬 Investigations / Workup:</h4>')
        .replace(/\*\*Management:\*\*/g, '<h4>💊 Management:</h4>')
        .replace(/\*\*Red Flags:\*\*/g, '<h4 style="color: #dc3545;">🚩 Red Flags:</h4>');
    
    // Format numbered lists (1. 2. 3.)
    formattedResponse = formattedResponse.replace(/^(\d+)\.\s+(.*)$/gm, '<div class="numbered-item"><span class="number">$1.</span> $2</div>');
    
    // Format bullet points (- or *)
    formattedResponse = formattedResponse.replace(/^[-*]\s+(.*)$/gm, '<div class="bullet-item">• $1</div>');
    
    // Format blockquotes (> text)
    formattedResponse = formattedResponse.replace(/^>\s+(.*)$/gm, '<blockquote>$1</blockquote>');
    
    // Format horizontal rules (--- or ***)
    formattedResponse = formattedResponse.replace(/^[-*]{3,}$/gm, '<hr>');
    
    // Format line breaks and paragraphs properly
    // First, protect existing HTML elements
    const protectedElements = [];
    formattedResponse = formattedResponse.replace(/<[^>]+>/g, (match) => {
        protectedElements.push(match);
        return `__PROTECTED_${protectedElements.length - 1}__`;
    });
    
    // Split into lines and process each line
    const lines = formattedResponse.split('\n');
    const processedLines = [];
    let inList = false;
    let inCodeBlock = false;
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        // Skip empty lines
        if (!line) {
            processedLines.push('');
            continue;
        }
        
        // Check for headers (already processed above)
        if (line.startsWith('<h')) {
            processedLines.push(line);
            continue;
        }
        
        // Check for list items (already processed above)
        if (line.startsWith('<div class="numbered-item">') || line.startsWith('<div class="bullet-item">')) {
            if (!inList) {
                inList = true;
            }
            processedLines.push(line);
            continue;
        } else if (inList) {
            inList = false;
        }
        
        // Check for blockquotes (already processed above)
        if (line.startsWith('<blockquote>')) {
            processedLines.push(line);
            continue;
        }
        
        // Check for horizontal rules (already processed above)
        if (line.startsWith('<hr>')) {
            processedLines.push(line);
            continue;
        }
        
        // Check for code blocks
        if (line.startsWith('<pre class="code-block">')) {
            inCodeBlock = true;
            processedLines.push(line);
            continue;
        } else if (inCodeBlock && line.includes('</pre>')) {
            inCodeBlock = false;
            processedLines.push(line);
            continue;
        } else if (inCodeBlock) {
            processedLines.push(line);
                continue;
        }
        
        // Regular paragraph content
        processedLines.push(`<p>${line}</p>`);
    }
    
    // Join lines and restore protected elements
    formattedResponse = processedLines.join('\n');
    protectedElements.forEach((element, index) => {
        formattedResponse = formattedResponse.replace(`__PROTECTED_${index}__`, element);
    });
    
    // Clean up empty paragraphs
    formattedResponse = formattedResponse.replace(/<p><\/p>/g, '');
    formattedResponse = formattedResponse.replace(/<p>\s*<\/p>/g, '');
    
    // Clean up multiple consecutive line breaks
    formattedResponse = formattedResponse.replace(/\n{3,}/g, '\n\n');
    
    // Highlight disclaimers
    formattedResponse = formattedResponse.replace(
        /(This application is for clinical decision support.*?\.)/gi,
        '<div class="disclaimer">$1</div>'
    );
    
    // Format probability percentages
    formattedResponse = formattedResponse.replace(
        /(\d+)%/g,
        '<span class="probability-badge">$1%</span>'
    );
    
    return formattedResponse;
}

function formatJSONResponse(response) {
    try {
        const data = JSON.parse(response);
        console.log('🎨 [Frontend] Parsing JSON response:', data);
        
        let html = '<div class="diagnosis-card">';
            
            // Clinical Overview
            if (data.clinical_overview) {
                html += `
                <h3>🏥 Clinical Assessment</h3>
                <div class="case-discussion">
                    <p>${data.clinical_overview}</p>
                    </div>
                `;
            }
            
            // Critical Alert
            if (data.critical_alert) {
                html += `
                <div class="critical-alert">
                    <h4 style="color: #dc3545;">🚨 CRITICAL ALERT</h4>
                    <p>This case requires immediate attention and urgent intervention.</p>
                    </div>
                `;
            }
            
            // Differential Diagnoses
        if (data.differential_diagnoses && data.differential_diagnoses.length > 0) {
                html += `
                <div class="differential-diagnoses-section">
                    <h4>🔍 Differential Diagnoses</h4>
                    <div class="diagnoses-grid">
            `;
            
            // Sort diagnoses by probability (highest first)
            const sortedDiagnoses = data.differential_diagnoses.sort((a, b) => 
                (b.probability_percent || 0) - (a.probability_percent || 0)
            );
            
            sortedDiagnoses.forEach((diagnosis, index) => {
                    const probability = diagnosis.probability_percent || 0;
                const probabilityColor = probability >= 70 ? '#dc3545' : probability >= 40 ? '#fd7e14' : '#28a745';
                const probabilityText = probability >= 70 ? 'High' : probability >= 40 ? 'Moderate' : 'Low';
                const rank = index + 1;
                    
                    html += `
                    <div class="diagnosis-card-item">
                        <div class="diagnosis-rank">#${rank}</div>
                        <div class="diagnosis-content">
                            <div class="diagnosis-header">
                                <h5 class="diagnosis-title">${diagnosis.diagnosis}</h5>
                                <div class="probability-container">
                                    <span class="probability-badge" style="background: ${probabilityColor}">
                                        ${probability}%
                                    </span>
                                    <span class="probability-label">${probabilityText} Probability</span>
                                </div>
                            </div>
                            <div class="diagnosis-evidence">
                                <strong>Evidence:</strong> ${diagnosis.evidence}
                            </div>
                            ${diagnosis.citations && diagnosis.citations.length > 0 ? `
                                <div class="diagnosis-citations">
                                    <strong>📚 Sources:</strong> ${diagnosis.citations.join(', ')}
                                </div>
                            ` : ''}
                        </div>
                        </div>
                    `;
                });
                
                html += `
                        </div>
                    </div>
                `;
            }
            
            // Immediate Workup
        if (data.immediate_workup && data.immediate_workup.length > 0) {
                html += `
                <div class="workup-section">
                    <h4>⚕️ Immediate Workup</h4>
                    <ul>
            `;
            data.immediate_workup.forEach(item => {
                html += `<li>${item}</li>`;
            });
            html += `
                        </ul>
                    </div>
                `;
            }
            
            // Management
        if (data.management && data.management.length > 0) {
                html += `
                <div class="management-section">
                    <h4>💊 Management</h4>
                    <ul>
            `;
            data.management.forEach(item => {
                html += `<li>${item}</li>`;
            });
            html += `
                        </ul>
                    </div>
                `;
            }
            
            // Red Flags
        if (data.red_flags && data.red_flags.length > 0) {
                html += `
                <div class="red-flags-section">
                    <h4 style="color: #dc3545;">🚩 Red Flags</h4>
                    <ul>
            `;
            data.red_flags.forEach(flag => {
                html += `<li>${flag}</li>`;
            });
            html += `
                        </ul>
                    </div>
                `;
            }
            
            // Additional Information Needed
            if (data.additional_information_needed) {
                html += `
                <div class="additional-info">
                    <h4>❓ Additional Information Needed</h4>
                    <p>${data.additional_information_needed}</p>
                    </div>
                `;
            }
            
        // Sources
        if (data.sources_used && data.sources_used.length > 0) {
                html += `
                <div class="sources">
                    <strong>📚 Sources Used:</strong> ${data.sources_used.join(', ')}
                    </div>
                `;
            }
            
        html += '</div>';
        return html;
        
    } catch (error) {
        console.error('Error parsing JSON response:', error);
        return `<div class="error-message">Error parsing AI response: ${error.message}</div>`;
    }
}

function formatDifferentialDiagnosis(response) {
    // Extract the main title
    const mainTitle = response.match(/\*\*DIFFERENTIAL DIAGNOSIS\*\*/)?.[0] || '**DIFFERENTIAL DIAGNOSIS**';
    
    // Extract case discussion
    const caseDiscussionMatch = response.match(/\*\*Case Discussion:\*\*([\s\S]*?)(?=\*\*Most Likely Diagnoses:\*\*|\*\*Expanded Differential:\*\*|$)/);
    const caseDiscussion = caseDiscussionMatch ? caseDiscussionMatch[1].trim() : '';
    
    // Extract most likely diagnoses
    const mostLikelyMatch = response.match(/\*\*Most Likely Diagnoses:\*\*([\s\S]*?)(?=\*\*Expanded Differential:\*\*|$)/);
    const mostLikely = mostLikelyMatch ? mostLikelyMatch[1].trim() : '';
    
    // Extract expanded differential
    const expandedMatch = response.match(/\*\*Expanded Differential:\*\*([\s\S]*?)(?=\*\*Sources:\*\*|$)/);
    const expanded = expandedMatch ? expandedMatch[1].trim() : '';
    
    // Extract sources
    const sourcesMatch = response.match(/\*\*Sources:\*\*([\s\S]*?)(?=\*This application.*|$)/);
    const sources = sourcesMatch ? sourcesMatch[1].trim() : '';
    
    // Extract disclaimer
    const disclaimerMatch = response.match(/\*This application.*\*/);
    const disclaimer = disclaimerMatch ? disclaimerMatch[0] : '';
    
    let formattedHTML = `
        <div class="diagnosis-card">
            <h3>${mainTitle.replace(/\*\*/g, '')}</h3>
    `;
    
    if (caseDiscussion) {
        formattedHTML += `
            <div class="case-discussion">
                <h4>Case Discussion</h4>
                <p>${formatText(caseDiscussion)}</p>
                    </div>
        `;
    }
    
    if (mostLikely) {
        formattedHTML += `
            <div class="diagnosis-list">
                <h4>Most Likely Diagnoses</h4>
                ${formatDiagnosisList(mostLikely)}
                    </div>
        `;
    }
    
    if (expanded) {
        formattedHTML += `
            <div class="diagnosis-list">
                <h4>Expanded Differential</h4>
                ${formatDiagnosisList(expanded)}
                </div>
            `;
    }
    
    if (sources) {
        formattedHTML += `
            <div class="sources">
                <strong>Sources:</strong> ${formatText(sources)}
            </div>
        `;
    }
    
    if (disclaimer) {
        formattedHTML += `
            <div class="disclaimer">
                ${disclaimer.replace(/\*/g, '')}
            </div>
        `;
    }
    
    formattedHTML += '</div>';
    
    return formattedHTML;
}

function formatDiagnosisList(text) {
    // Split by bullet points or numbered items
    const items = text.split(/(?=^- |^-\s|\d+\.\s)/).filter(item => item.trim());
    
    if (items.length > 0) {
        let html = '<ul>';
        items.forEach(item => {
            if (item.trim()) {
                html += `<li>${formatText(item.replace(/^[-•\d\.\s]+/, ''))}</li>`;
            }
        });
        html += '</ul>';
        return html;
    }
    
    return `<p>${formatText(text)}</p>`;
}

function formatText(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`\[Source: (.*?)\]`/g, '<em>[Source: $1]</em>')
        .replace(/\n/g, '<br>')
        .trim();
}

function formatChatHistory() {
    if (chatHistory.length === 0) return '';
    
    return chatHistory.map(entry => 
        `Lawyer: ${entry.user}\nAI Assistant: ${entry.ai}`
    ).join('\n\n');
}

// Sample Question Functions
function useSamplePrompt(type) {
    const sampleQuestions = {
        // Backward-compatible keys
        'chest-pain': 'Adult patient presents with chest pain, shortness of breath, and diaphoresis. What are the differential diagnoses?',
        'fever': '5-year-old child with persistent high fever (39.5°C) for 3 days, no obvious cause. What should I consider?',
        'pediatric': 'Infant with respiratory distress, wheezing, and feeding difficulties. What are the possible causes?',
        'abdominal': 'Adult with acute severe abdominal pain, nausea, and vomiting. What diagnostic approach should I take?',

        // Differential Diagnosis
        'ddx_chest_pain': 'Adult patient presents with chest pain, shortness of breath, and diaphoresis. What are the differential diagnoses?',
        'ddx_abdominal_pain': 'Adult with acute severe abdominal pain and vomiting. Outline initial differential diagnoses and workup.',

        // Pediatrics
        'peds_fever': '5-year-old child with persistent high fever (39.5°C) for 3 days, no obvious cause. What should I consider?',
        'peds_wheezing': 'Infant with respiratory distress, wheezing, and feeding difficulties. What are the possible causes and red flags?',

        // Drug Information
        'drug_paracetamol': 'Provide drug information for Paracetamol: indications, adult dosing, contraindications, and key interactions.',
        'drug_amoxicillin': 'Provide drug information for Amoxicillin: indications, pediatric dosing, common side effects, and interactions.',

        // Clinical Guidance
        'guideline_stemi': 'Suspected STEMI in the ER — summarize immediate management steps and critical time targets.',
        'guideline_preeclampsia': 'Third-trimester patient with severe hypertension — outline management for preeclampsia with severe features.',

        // New: Ask about drug dosing
        'dosing_ceftriaxone_pneumonia_adult60': 'Calculate the dose for ceftriaxone for a 60kg adult with severe pneumonia',
        'dosing_insulin_dka': 'How is insulin dosed during diabetic ketoacidosis(DKA) management?',

        // New: Ask about Drug interactions
        'interact_ritonavir_simvastatin': 'An HIV patient on ritonavir is started on simvastatin. What adverse effect might occur and why?',
        'interact_warfarin_greens': 'What happens when green leafy vegetables are taken in large amounts while on warfarin?',

        // New: About Guidelines
        'guideline_ada_t2dm_insulin_init': 'What are the ADA(American Diabates Association) recommendations for initiating insulin therapy in type 2 diabetes',
        'guideline_who_malaria_pregnancy': 'According to Who Malaria guidelines, how should malaria in pregnancy be treated?',

        // New: Treatment Options
        'tx_severe_malnutrition_u5': 'What are the treatmmet options for severe malnutrition in children under 5',
        'tx_stage1_hypertension_firstline': 'What is the first line antihypertensive medications for stage 1 hypertension?'
    };

    // Try dashboard input first, then landing input
    const dashboardInput = document.getElementById('dashboardMessageInput');
    const landingInput = document.getElementById('landingMessageInput');
    const messageInput = dashboardInput || landingInput;

    if (messageInput && sampleQuestions[type]) {
        messageInput.value = sampleQuestions[type];
        messageInput.focus();
        autoResizeTextarea.call(messageInput);

        // Force update of send button state since programmatic value setting doesn't trigger input events
        updateSendButton();
    }
}

// Session Management
async function createSession() {
    try {
        console.log('📝 [Frontend] Creating new chat session');
        const response = await fetch(`${API_URL}/chat/sessions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({
                session_name: `Session ${new Date().toLocaleDateString()}`,
                case_summary: ''
            })
        });
        
        const data = await response.json();
        console.log('📝 [Frontend] Session creation response:', data);
        
        if (data.success) {
            return data.data;
        } else {
            throw new Error('Failed to create session');
        }
    } catch (error) {
        console.error('Error creating session:', error);
        return null;
    }
}

async function loadUserSessions() {
    try {
        const response = await fetch(`${API_URL}/chat/sessions`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateSessionsList(data.data.sessions || data.data);
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

function updateSessionsList(sessions) {
    const sessionsList = document.getElementById('sessionsList');
    const emptyState = document.getElementById('emptySessionsState');
    if (!sessionsList) return;
    
    // Clear existing sessions (but keep empty state)
    const existingSessions = sessionsList.querySelectorAll('.session-item');
    existingSessions.forEach(item => item.remove());
    
    // Show/hide empty state
    if (sessions && sessions.length > 0) {
        if (emptyState) emptyState.style.display = 'none';
        
        sessions.forEach(session => {
            const sessionItem = document.createElement('div');
            sessionItem.className = 'session-item';
            sessionItem.innerHTML = `
                <div class="session-name">Session ${session.id}</div>
                <div class="session-date">${new Date(session.created_at).toLocaleDateString()}</div>
            `;
            
            // Add keyboard accessibility
            sessionItem.setAttribute('role', 'button');
            sessionItem.setAttribute('tabindex', '0');
            sessionItem.setAttribute('aria-label', `Load Session ${session.id}`);
            
            sessionItem.addEventListener('click', () => {
                // Remove active class from all items
                document.querySelectorAll('.session-item').forEach(item => item.classList.remove('active'));
                // Add active class to clicked item
                sessionItem.classList.add('active');
                loadSession(session);
            });
            
            // Keyboard support
            sessionItem.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    sessionItem.click();
                }
            });
            
            sessionsList.appendChild(sessionItem);
        });
    } else {
        if (emptyState) emptyState.style.display = 'flex';
    }
}

async function loadSession(session) {
    console.log('📂 [Frontend] Loading session:', session);
    currentSession = session;
    
    try {
        // Load session messages
        const response = await fetch(`${API_URL}/chat/sessions/${session.id}/messages`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            }
        });
        
        const data = await response.json();
        console.log('📂 [Frontend] Session messages response:', data);
        
        if (data.success) {
            const messages = data.data.messages || [];
            console.log('📂 [Frontend] Loaded messages:', messages);
            
            // Clear current chat
            const dashboardChat = document.getElementById('dashboardChatMessages');
            const landingChat = document.getElementById('landingChatMessages');
            const chatMessages = dashboardChat || landingChat;
            
            if (chatMessages) {
                chatMessages.innerHTML = '';
            }
            
            // Add welcome message
            const welcomeDiv = document.createElement('div');
            welcomeDiv.className = 'welcome-message';
            welcomeDiv.innerHTML = `
                <div class="welcome-content">
                    <h3>Session: ${session.session_name || `Session #${session.id}`}</h3>
                    <p>Continuing previous conversation...</p>
                </div>
            `;
            if (chatMessages) {
                chatMessages.appendChild(welcomeDiv);
                
                // Add all messages from the session
                messages.forEach(message => {
                    const isUser = message.message_type === 'user';
                    const status = isUser ? 'user' : 'ai';
                    addMessage(message.content, [], status, isUser);
                });
                
                // Update chat history
                chatHistory = messages.map(msg => ({
                    user: msg.message_type === 'user' ? msg.content : null,
                    ai: msg.message_type === 'assistant' ? msg.content : null
                })).filter(msg => msg.user || msg.ai);
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
        } else {
            console.error('Failed to load session messages');
        }
    } catch (error) {
        console.error('Error loading session:', error);
    }
}

function startNewChat() {
    // Alias for startNewSession for the UI button
    startNewSession();
}

function startNewSession() {
    currentSession = null;
    chatHistory = [];
    clearChat();
    
    // Update sidebar
    const sessionItems = document.querySelectorAll('.session-item');
    sessionItems.forEach(item => item.classList.remove('active'));
    
    console.log('🆕 [Frontend] Started new session - will create when first message is sent');
}

function clearChat() {
    // Clear chat container
    const landingChat = document.getElementById('landingChatMessages');
    
    const welcomeHTML = `<br>
        <div class="welcome-message">
            <div class="welcome-content">
                <h1 class="welcome-logo">
                    <span class="logo-health">Legal</span><span class="logo-navy">AI</span>
                </h1>
                <p>Guiding your legal practice.</p>
                <br>
                <span>LegalAI is a legal information platform intended for use by qualified legal professionals as a reference tool <br> to access evidence-based legal information.</span>
                <br><br>
            </div>
        </div>
    `;
    
    if (landingChat) {
        landingChat.innerHTML = welcomeHTML;
    }
    
    chatHistory = [];
}

// Utility Functions
function autoResizeTextarea() {
    const textarea = this;
    
            textarea.style.height = 'auto';
            const scrollHeight = textarea.scrollHeight;
            const minHeight = 24;
            const maxHeight = 120;
            
            const newHeight = Math.max(minHeight, Math.min(scrollHeight, maxHeight));
            textarea.style.height = newHeight + 'px';
            
            if (scrollHeight > maxHeight) {
                textarea.style.overflowY = 'auto';
            } else {
                textarea.style.overflowY = 'hidden';
    }
    
    // Enable/disable send buttons based on input content
    const value = textarea.value || '';
    const hasContent = value.trim().length > 0;
    
    const dashboardButton = document.getElementById('dashboardSendButton');
    const landingButton = document.getElementById('landingSendButton');
    
    if (dashboardButton) {
        dashboardButton.disabled = !hasContent;
    }
    if (landingButton) {
        setSendButtonEnabled(hasContent);
    }
}


// Global functions for HTML onclick handlers
window.showAuthModal = showAuthModal;
window.closeAuthModal = closeAuthModal;
window.toggleAuthMode = toggleAuthMode;
window.togglePasswordVisibility = togglePasswordVisibility;
window.sendMessage = sendMessage;
window.useSamplePrompt = useSamplePrompt;
window.logout = logout;
window.startNewSession = startNewSession;
window.showTerms = showTerms;
window.showPrivacy = showPrivacy;
window.showSupport = showSupport;

// Password visibility toggle function
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const toggle = input.parentElement.querySelector('.password-toggle i');
    
    if (input.type === 'password') {
        input.type = 'text';
        toggle.className = 'fas fa-eye-slash';
        toggle.setAttribute('aria-label', 'Hide password');
        } else {
        input.type = 'password';
        toggle.className = 'fas fa-eye';
        toggle.setAttribute('aria-label', 'Show password');
    }
}

// Footer link functions
function showTerms() {
    alert('Terms of Service: Please note that LegalAI is designed for legal decision support and should not replace professional legal judgment. All users must comply with applicable legal regulations and privacy requirements.');
}

function showPrivacy() {
    alert('Privacy Policy: Your legal information is protected and encrypted. We comply with applicable regulations and only process data necessary for providing legal decision support.');
}

function showSupport() {
    alert('Support: For technical support or legal assistance, please contact us at support@legalai.com or visit our help center.');
}

// ===== THEME MANAGEMENT =====
function initializeTheme() {
    console.log('🎨 Initializing theme system...');
    // Check for saved theme preference or default to system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme) {
        currentTheme = savedTheme;
        console.log('🎨 Loaded saved theme:', savedTheme);
    } else if (systemPrefersDark) {
        currentTheme = 'dark';
        console.log('🎨 Using system preference: dark');
    } else {
        currentTheme = 'light';
        console.log('🎨 Using default theme: light');
    }
    
    applyTheme(currentTheme);
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            currentTheme = e.matches ? 'dark' : 'light';
            applyTheme(currentTheme);
        }
    });
    
    console.log('🎨 Theme system initialized successfully');
}

function toggleTheme() {
    console.log('🎨 Toggle theme called. Current theme:', currentTheme);
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    console.log('🎨 New theme:', currentTheme);
    applyTheme(currentTheme);
    localStorage.setItem('theme', currentTheme);
}

// Make toggleTheme available globally (for onclick handlers)
window.toggleTheme = toggleTheme;

function applyTheme(theme) {
    console.log('🎨 Applying theme:', theme);
    const html = document.documentElement;
    const themeIcon = document.getElementById('themeIcon');
    const sidebarThemeIcon = document.getElementById('sidebarThemeIcon');
    
    console.log('🎨 HTML element:', html);
    console.log('🎨 Theme icon:', themeIcon);
    console.log('🎨 Sidebar theme icon:', sidebarThemeIcon);
    
    if (theme === 'dark') {
        html.setAttribute('data-theme', 'dark');
        console.log('🎨 Set data-theme to dark');
        if (themeIcon) {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
        }
        if (sidebarThemeIcon) {
            sidebarThemeIcon.classList.remove('fa-sun');
            sidebarThemeIcon.classList.add('fa-moon');
        }
    } else {
        html.removeAttribute('data-theme');
        console.log('🎨 Removed data-theme attribute (light mode)');
        if (themeIcon) {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        }
        if (sidebarThemeIcon) {
            sidebarThemeIcon.classList.remove('fa-moon');
            sidebarThemeIcon.classList.add('fa-sun');
        }
    }
    
    currentTheme = theme;
    console.log('🎨 Theme applied. Current theme is now:', currentTheme);
    console.log('🎨 HTML data-theme attribute:', html.getAttribute('data-theme'));
}