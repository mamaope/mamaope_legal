// mamaope_legal AI Authentication Application
class mamaope_legalAuth {
    constructor() {
        this.API_URL = '/api/v1'; // Direct connection to backend
        this.currentTab = 'login';
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.updateAuthUI();
        this.hideLoading(); // Ensure loading is hidden on init
    }
    
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.remove('show');
        }
    }
    
    showLoading(text = 'Loading...') {
        const overlay = document.getElementById('loadingOverlay');
        const loadingText = document.getElementById('loadingText');
        if (overlay && loadingText) {
            loadingText.textContent = text;
            overlay.classList.add('show');
        }
    }
    
    setupEventListeners() {
        // Password strength checker
        const passwordInput = document.getElementById('registerPassword');
        if (passwordInput) {
            passwordInput.addEventListener('input', () => this.checkPasswordStrength());
        }
        
        // Form validation
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                if (form.id === 'loginForm') {
                    this.loginUser();
                } else if (form.id === 'registerForm') {
                    this.registerUser();
                }
            });
        });
    }
    
    updateAuthUI() {
        const title = document.getElementById('authTitle');
        const subtitle = document.getElementById('authSubtitle');
        
        if (this.currentTab === 'login') {
            title.textContent = 'Welcome Back';
            subtitle.textContent = 'Sign in to your mamaope_legal account';
        } else {
            title.textContent = 'Create Account';
            subtitle.textContent = 'Join mamaope_legal AI today';
        }
    }
    
    switchAuthTab(tab) {
        this.currentTab = tab;
        
        // Update tabs
        document.querySelectorAll('.auth-tab').forEach(tabEl => {
            tabEl.classList.remove('active');
        });
        
        document.getElementById(`${tab}Tab`).classList.add('active');
        
        // Update forms
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.remove('active');
        });
        
        document.getElementById(`${tab}FormContainer`).classList.add('active');
        
        // Clear messages
        this.hideMessage();
        
        // Update UI
        this.updateAuthUI();
    }
    
    showMessage(message, type = 'error') {
        const messageEl = document.getElementById('authMessage');
        const iconEl = messageEl.querySelector('.message-icon');
        const textEl = messageEl.querySelector('.message-text');
        
        messageEl.className = `auth-message ${type}`;
        
        // Set icon based on type
        switch(type) {
            case 'success':
                iconEl.className = 'message-icon fas fa-check-circle';
                break;
            case 'error':
                iconEl.className = 'message-icon fas fa-exclamation-circle';
                break;
            case 'info':
                iconEl.className = 'message-icon fas fa-info-circle';
                break;
        }
        
        textEl.textContent = message;
        messageEl.style.display = 'flex';
        
        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => this.hideMessage(), 5000);
        }
    }
    
    showFieldError(fieldId, message) {
        const field = document.getElementById(fieldId);
        if (!field) return;
        
        // Remove existing error styling
        field.classList.remove('error');
        
        // Add error styling
        field.classList.add('error');
        
        // Show error message
        this.showMessage(message, 'error');
        
        // Focus the field
        field.focus();
    }
    
    clearFieldError(fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.classList.remove('error');
        }
    }
    
    hideMessage() {
        const messageEl = document.getElementById('authMessage');
        messageEl.style.display = 'none';
    }
    
    setLoading(buttonId, loading = true) {
        const button = document.getElementById(buttonId);
        const span = button.querySelector('span');
        const loadingEl = button.querySelector('.btn-loading');
        
        if (loading) {
            button.disabled = true;
            span.style.opacity = '0';
            loadingEl.style.display = 'block';
        } else {
            button.disabled = false;
            span.style.opacity = '1';
            loadingEl.style.display = 'none';
        }
    }
    
    checkPasswordStrength() {
        const password = document.getElementById('registerPassword').value;
        const strengthBar = document.querySelector('.strength-fill');
        const strengthText = document.querySelector('.strength-text');
        
        if (!password) {
            strengthBar.style.width = '0%';
            strengthText.textContent = 'Password strength';
            return;
        }
        
        let score = 0;
        let feedback = '';
        
        // Length check
        if (password.length >= 12) score += 1;
        else feedback = 'Use at least 12 characters';
        
        // Character variety checks
        if (/[a-z]/.test(password)) score += 1;
        if (/[A-Z]/.test(password)) score += 1;
        if (/[0-9]/.test(password)) score += 1;
        if (/[^A-Za-z0-9]/.test(password)) score += 1;
        
        // Update strength bar
        const strengthClasses = ['weak', 'fair', 'good', 'strong'];
        const strengthLabels = ['Weak', 'Fair', 'Good', 'Strong'];
        
        strengthBar.className = `strength-fill ${strengthClasses[Math.min(score, 3)]}`;
        strengthText.textContent = feedback || `Password strength: ${strengthLabels[Math.min(score, 3)]}`;
    }
    
    togglePassword(inputId) {
        const input = document.getElementById(inputId);
        const toggle = input.parentElement.querySelector('.password-toggle i');
        
        if (input.type === 'password') {
            input.type = 'text';
            toggle.className = 'fas fa-eye-slash';
        } else {
            input.type = 'password';
            toggle.className = 'fas fa-eye';
        }
    }
    
    async loginUser() {
        const email = document.getElementById('loginEmail').value.trim();
        const password = document.getElementById('loginPassword').value;
        
        // Clear previous errors
        this.hideMessage();
        ['loginEmail', 'loginPassword'].forEach(fieldId => {
            this.clearFieldError(fieldId);
        });
        
        // Validation
        if (!email) {
            this.showFieldError('loginEmail', 'Email address is required');
            return;
        }
        
        if (!this.isValidEmail(email)) {
            this.showFieldError('loginEmail', 'Please enter a valid email address');
            return;
        }
        
        if (!password) {
            this.showFieldError('loginPassword', 'Password is required');
            return;
        }
        
        this.setLoading('loginSubmitBtn', true);
        
        try {
            const response = await this.apiCall('/auth/login', 'POST', {
                email: email,
                password: password
            });
            
            if (response.success) {
                // Store authentication data
                localStorage.setItem('accessToken', response.data.access_token);
                localStorage.setItem('currentUser', JSON.stringify(response.data.user));
                
                this.showMessage('Login successful! Redirecting...', 'success');
                
                // Redirect to dashboard
                setTimeout(() => {
                    window.location.href = '/';
                }, 1500);
            } else {
                this.showMessage(response.data?.message || 'Login failed. Please check your credentials.', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showMessage('Network error. Please try again.', 'error');
        } finally {
            this.setLoading('loginSubmitBtn', false);
        }
    }
    
    async registerUser() {
        const firstName = document.getElementById('registerFirstName').value.trim();
        const lastName = document.getElementById('registerLastName').value.trim();
        const email = document.getElementById('registerEmail').value.trim();
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('registerConfirmPassword').value;
        const agreeTerms = document.getElementById('agreeTerms').checked;
        
        // Clear previous errors
        this.hideMessage();
        ['registerFirstName', 'registerLastName', 'registerEmail', 'registerPassword', 'registerConfirmPassword'].forEach(fieldId => {
            this.clearFieldError(fieldId);
        });
        
        // Validation
        if (!firstName) {
            this.showFieldError('registerFirstName', 'First name is required');
            return;
        }
        
        if (!lastName) {
            this.showFieldError('registerLastName', 'Last name is required');
            return;
        }
        
        if (!email) {
            this.showFieldError('registerEmail', 'Email address is required');
            return;
        }
        
        if (!this.isValidEmail(email)) {
            this.showFieldError('registerEmail', 'Please enter a valid email address');
            return;
        }
        
        if (!password) {
            this.showFieldError('registerPassword', 'Password is required');
            return;
        }
        
        if (password.length < 12) {
            this.showFieldError('registerPassword', 'Password must be at least 12 characters long');
            return;
        }
        
        if (!confirmPassword) {
            this.showFieldError('registerConfirmPassword', 'Please confirm your password');
            return;
        }
        
        if (password !== confirmPassword) {
            this.showFieldError('registerConfirmPassword', 'Passwords do not match');
            return;
        }
        
        if (!agreeTerms) {
            this.showMessage('Please agree to the Terms of Service and Privacy Policy', 'error');
            return;
        }
        
        this.setLoading('registerSubmitBtn', true);
        
        try {
            const response = await this.apiCall('/auth/register', 'POST', {
                first_name: firstName,
                last_name: lastName,
                email: email,
                password: password
            });
            
            if (response.success) {
                this.showMessage('Account created successfully! Please check your email for verification.', 'success');
                
                // Clear form
                document.getElementById('registerForm').reset();
                this.checkPasswordStrength();
                
                // Switch to login tab after 3 seconds
                setTimeout(() => {
                    this.switchAuthTab('login');
                }, 3000);
            } else {
                this.showMessage(response.data?.message || 'Registration failed. Please try again.', 'error');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.showMessage('Network error. Please try again.', 'error');
        } finally {
            this.setLoading('registerSubmitBtn', false);
        }
    }
    
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    async apiCall(endpoint, method = 'GET', data = null) {
        const baseUrl = window.location.origin;
        const fullUrl = `${baseUrl}${this.API_URL}${endpoint}`;
        
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(fullUrl, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.data?.message || `HTTP error! status: ${response.status}`);
        }
        
        return result;
    }
    
    showForgotPassword() {
        this.showMessage('Password reset functionality coming soon. Please contact support.', 'info');
    }
    
    showTerms() {
        this.showMessage('Terms of Service will be available soon.', 'info');
    }
    
    showPrivacy() {
        this.showMessage('Privacy Policy will be available soon.', 'info');
    }
    
    showSupport() {
        this.showMessage('Support: support@mamaope_legal.ai', 'info');
    }
}

// Global functions for HTML onclick handlers
window.switchAuthTab = (tab) => app.switchAuthTab(tab);
window.togglePassword = (inputId) => app.togglePassword(inputId);
window.showForgotPassword = () => app.showForgotPassword();
window.showTerms = () => app.showTerms();
window.showPrivacy = () => app.showPrivacy();
window.showSupport = () => app.showSupport();

// Initialize the authentication application
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new mamaope_legalAuth();
});
