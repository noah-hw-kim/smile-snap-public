// js/admin.js - Admin dashboard specific logic
// Protect this page
if (!checkAccess('admin')) {
    throw new Error('Access denied');
}

document.addEventListener('DOMContentLoaded', () => {
    // console.log('🔴 DOM Content Loaded - admin.js');
    
    // Initialize admin dashboard
    initializeAdminDashboard();
    
    // Fetch and display users
    fetchAllUsers();
    
    // Set up event listeners
    setupAdminEventListeners();
    // console.log('🔴 Admin event listeners setup complete');
});

function initializeAdminDashboard() {
    // Update admin info display
    const adminInfo = document.getElementById('adminInfo');
    if (adminInfo) {
        adminInfo.textContent = `Admin: ${state.email}`;
    }
    
    console.log('Admin dashboard initialized for:', state.email);
}

async function fetchAllUsers() {
    try {
        const users = await apiFetch('/admin/users');
        renderUsersList(users);
        setupDeleteButtonListeners();
    } catch (error) {
        console.error('Failed to fetch users:', error);
        showAlert('Failed to load users: ' + error.message, 'danger');
    }
}

function renderUsersList(users) {
    const usersList = document.getElementById('usersList');
    if (!users || users.length === 0) {
        usersList.innerHTML = '<p class="text-muted text-center">No users found.</p>';
        return;
    }
    
    usersList.innerHTML = users.map(user => `
        <div class="card mb-2 user-item" data-user-id="${user.userId}">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1" style="cursor: pointer;" onclick="viewUser('${user.userId}')">
                        <h6 class="mb-1">${user.displayName}</h6>
                        <p class="mb-1"><strong>Email:</strong> ${user.email}</p>
                        <p class="mb-1">
                            <strong>Role:</strong> 
                            <span class="badge ${user.role === 'admin' ? 'bg-danger' : 'bg-primary'}">${user.role}</span>
                        </p>
                        <p class="mb-0">
                            <small class="text-muted">
                                <i class="bi bi-calendar3"></i> Registered: ${new Date(user.createdAt).toLocaleString()}
                            </small>
                        </p>
                    </div>
                    <div class="ms-3 d-flex flex-column gap-1">
                        <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); viewUser('${user.userId}')">
                            <i class="bi bi-eye"></i> View
                        </button>
                        <button class="btn btn-sm btn-danger delete-user-btn" 
                                data-user-id="${user.userId}" 
                                data-user-email="${user.email}">
                            <i class="bi bi-trash"></i> Delete
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');

    // console.log('🔴 Users rendered, buttons should be clickable now');
}

function testClick() {
    console.log('🔴 TEST CLICK WORKS!');
}

function setupDeleteButtonListeners() {
    // console.log('🔴 Setting up delete button listeners...');
    
    // Add the listener
    document.addEventListener('click', handleDeleteClick);

    // console.log('🔴 Event listener added. Testing...');
}

async function handleDeleteClick(e) {
    // console.log('🔴 Document clicked!', e.target);
    // console.log('🔴 Target classes:', e.target.classList);
    
    let deleteBtn = null;
    
    if (e.target.classList.contains('delete-user-btn')) {
        deleteBtn = e.target;
    } else if (e.target.closest('.delete-user-btn')) {
        deleteBtn = e.target.closest('.delete-user-btn');
    }
    
    if (deleteBtn) {
        // console.log('🔴 Delete button found!', deleteBtn);
        
        const userId = deleteBtn.dataset.userId;
        const userEmail = deleteBtn.dataset.userEmail;
        
        // console.log('🔴 User ID:', userId, 'Email:', userEmail);
        
        const originalHtml = deleteBtn.innerHTML;
        setLoading(deleteBtn, true, originalHtml);
        
        try {
            const success = await deleteUser(userId, userEmail);
            
            if (!success) {
                deleteBtn.innerHTML = originalHtml;
                deleteBtn.disabled = false;
            }
        } catch (error) {
            console.error('Delete user error:', error);
            deleteBtn.innerHTML = originalHtml;
            deleteBtn.disabled = false;
        }
    }
}

function viewUser(userId) {
    // Redirect to user dashboard with view parameter
    window.location.href = `user.html?viewUser=${userId}`;
}

function refreshUsers() {
    fetchAllUsers();
}

async function deleteUser(userId, userEmail) {
    // Prevent admin from deleting themselves
    if (userId === state.userId) {
        showAlert('You cannot delete your own account from the admin panel.', 'warning');
        return;
    }
    
    // Double confirmation
    const confirmMessage = `⚠️ WARNING: This action cannot be undone!\n\nThis will permanently delete user "${userEmail}" and:\n- All their photos\n- All their diary entries\n- All associated data\n\nType "DELETE" to confirm:`;
    
    const userInput = prompt(confirmMessage);
    
    if (userInput === 'DELETE') {
        const finalConfirm = confirm(`Are you absolutely sure you want to delete user "${userEmail}"?`);
        
        if (finalConfirm) {
            try {
                await apiFetch(`/users/${userId}`, { method: 'DELETE' });
                showAlert(`User "${userEmail}" has been permanently deleted.`, 'success');
                fetchAllUsers(); // Refresh the list
                return true;
            } catch (error) {
                console.error('User deletion failed:', error);
                showAlert('Failed to delete user: ' + error.message, 'danger');
                return false;
            }
        }
    } else if (userInput !== null) {
        showAlert('User deletion cancelled. You must type "DELETE" exactly.', 'warning');
    }
    return false;
}

function setupAdminEventListeners() {
    // console.log('🔴 Setting up admin event listeners...');
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshUsers');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshUsers);
    }
}