// js/shared.js - Shared utilities across all pages

// Global state
let state = {
    token: null,
    userId: null,
    email: null,
    role: null,
    ws: null,
    currentViewUserId: null
};

// Initialize auth from localStorage
function initializeAuth() {
    const savedToken = localStorage.getItem('authToken');
    const savedUser = localStorage.getItem('user');
    
    if (savedToken && savedUser) {
        try {
            const user = JSON.parse(savedUser);
            state.token = savedToken;
            state.userId = user.userId;
            state.email = user.email;
            state.role = user.role;
            return true;
        } catch (error) {
            clearAuth();
            return false;
        }
    }
    return false;
}

// Clear authentication
function clearAuth() {
    state = { token: null, userId: null, email: null, role: null, ws: null, currentViewUserId: null };
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
}

// Authentication checks
function isAuthenticated() {
    return state.token && state.userId;
}

function isAdmin() {
    return state.role === 'admin';
}

function isUser() {
    return state.role === 'user';
}

// Page protection
function checkAccess(requiredRole = null) {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('user');
    
    if (!token || !user) {
        alert('🔒 Please login to access this page.');
        window.location.href = 'index.html';
        return false;
    }
    
    try {
        const userData = JSON.parse(user);
        
        if (requiredRole) {
            if (requiredRole === 'admin' && userData.role !== 'admin') {
                alert(`🚫 Access denied. This page requires admin privileges.\n\nYour role: ${userData.role}`);
                window.location.href = 'user.html';
                return false;
            }
            
            if (requiredRole === 'user' && userData.role !== 'user' && userData.role !== 'admin') {
                alert(`🚫 Access denied. Please login with a valid account.`);
                window.location.href = 'index.html';
                return false;
            }
        }
        
        return true;
    } catch (error) {
        localStorage.clear();
        alert('🔒 Session expired. Please login again.');
        window.location.href = 'index.html';
        return false;
    }
}

// API Helper
async function apiFetch(endpoint, options = {}) {
    options.headers = { ...options.headers };
    if (state.token) {
        options.headers['Authorization'] = `Bearer ${state.token}`;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        if (response.status === 204) return null;
        return response.json();
    } catch (error) {
        const message = error.message.includes('NetworkError') 
            ? 'Backend not responding - check if server is running'
            : error.message;
        showAlert(message);
        throw error;
    }
}

// UI Utilities
function showAlert(message, type = 'danger') {
    const alertContainer = document.getElementById('alertContainer');
    if (alertContainer) {
        alertContainer.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
    }
}

function setLoading(button, isLoading, originalText = 'Submit') {
    if (isLoading) {
        button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Loading...`;
        button.disabled = true;
    } else {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Logout function
function logout() {
    if (state.ws) state.ws.close();
    clearAuth();
    window.location.href = 'index.html';
}

// WebSocket helper
function connectWebSocket(userId = null) {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) return;
    
    const connectUserId = userId || state.userId;
    const wsUrl = `${WS_BASE_URL}/ws/updates/${connectUserId}?token=${encodeURIComponent(state.token)}`;
    
    console.log('🔴 Connecting WebSocket for user:', connectUserId);
    
    state.ws = new WebSocket(wsUrl);
    
    state.ws.onopen = () => {
        const wsStatus = document.getElementById('wsStatus');
        if (wsStatus) {
            wsStatus.textContent = 'WebSocket: Connected';
            wsStatus.className = 'badge bg-success';
        }
        console.log('🔴 WebSocket connected successfully');
    };
    
    state.ws.onclose = (event) => {
        const wsStatus = document.getElementById('wsStatus');
        if (wsStatus) {
            wsStatus.textContent = `WebSocket: Disconnected (${event.reason || 'Unknown'})`;
            wsStatus.className = 'badge bg-danger';
        }
        console.log('🔴 WebSocket disconnected:', event.reason);
    };
    
    state.ws.onerror = (error) => {
        console.error('🔴 WebSocket Error:', error);
        showAlert('WebSocket connection error.', 'warning');
    };
    
    return state.ws;
}

// Initialize auth on load
initializeAuth();