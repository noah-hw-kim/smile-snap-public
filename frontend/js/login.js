// js/login.js - Login page specific logic

document.addEventListener('DOMContentLoaded', () => {
    // If already logged in, redirect to appropriate page
    if (isAuthenticated()) {
        if (isAdmin()) {
            window.location.href = 'admin.html';
        } else {
            window.location.href = 'user.html';
        }
        return;
    }

    // UI Elements
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    // Registration handler
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('Registration form submitted');
            
            const submitBtn = e.target.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            
            setLoading(submitBtn, true);
            
            try {
                await apiFetch('/users/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: document.getElementById('registerEmail').value,
                        password: document.getElementById('registerPassword').value,
                        displayName: document.getElementById('displayName').value,
                        role: document.getElementById('userRole').value
                    })
                });
                showAlert('Registration successful! Please login.', 'success');
                registerForm.reset();
                
            } catch (error) {
                console.error('Registration failed:', error);
            } finally {
                setLoading(submitBtn, false, 'Register');
            }
        });
    }

    // Login handler
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = e.target.querySelector('button[type="submit"]');
            setLoading(submitBtn, true);
            
            const formData = new FormData();
            formData.append('username', document.getElementById('loginEmail').value);
            formData.append('password', document.getElementById('loginPassword').value);
            
            try {
                const data = await apiFetch('/token', { method: 'POST', body: formData });
                
                // Update state
                state.token = data.access_token;
                state.userId = data.user.userId;
                state.email = data.user.email;
                state.role = data.user.role;
                
                // Save to localStorage
                localStorage.setItem('authToken', state.token);
                localStorage.setItem('user', JSON.stringify(data.user));
                
                // Redirect based on role
                if (state.role === 'admin') {
                    showAlert(`Login successful! Redirecting to admin dashboard...`, 'success');
                    setTimeout(() => {
                        window.location.href = 'admin.html';
                    }, 1000);
                } else {
                    showAlert(`Login successful! Redirecting to user dashboard...`, 'success');
                    setTimeout(() => {
                        window.location.href = 'user.html';
                    }, 1000);
                }
                
            } catch (error) {
                console.error('Login failed:', error);
            } finally {
                setLoading(submitBtn, false, 'Login');
            }
        });
    }
});