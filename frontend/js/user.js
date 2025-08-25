// js/user.js - User dashboard specific logic

// Protect this page
if (!checkAccess('user')) {
    throw new Error('Access denied');
}

document.addEventListener('DOMContentLoaded', () => {
    // Check if admin is viewing another user's data
    const urlParams = new URLSearchParams(window.location.search);
    const viewUserId = urlParams.get('viewUser');
    
    if (viewUserId && isAdmin()) {
        state.currentViewUserId = viewUserId;
    }
    
    // Initialize user dashboard
    initializeUserDashboard();
    
    // Fetch user data
    fetchUserPhotos();
    fetchUserEntries();
    
    // Connect WebSocket
    connectUserWebSocket();
    
    // Set up event listeners
    setupUserEventListeners();
});

function initializeUserDashboard() {
    // Update user info display
    const userInfo = document.getElementById('userInfo');
    if (userInfo) {
        const displayText = state.currentViewUserId 
            ? `Admin viewing user data` 
            : `${state.role}: ${state.email}`;
        userInfo.textContent = displayText;
    }
    
    // Update page title if admin is viewing
    if (state.currentViewUserId) {
        const pageTitle = document.querySelector('h5');
        if (pageTitle) {
            pageTitle.textContent = '👁️ Viewing User Dashboard (Read Only)';
        }
    }
    
    // Hide/show upload form based on whether admin is viewing another user
    const uploadCard = document.querySelector('#userSection .card:first-child');
    if (uploadCard) {
        uploadCard.style.display = state.currentViewUserId ? 'none' : 'block';
    }
    
    // Navigation button visibility
    const backBtn = document.getElementById('backBtn');
    const deleteAccountBtn = document.getElementById('deleteAccountBtn');
    
    if (backBtn) {
        backBtn.style.display = state.currentViewUserId ? 'block' : 'none';
    }
    
    if (deleteAccountBtn) {
        deleteAccountBtn.style.display = state.token && !state.currentViewUserId ? 'block' : 'none';
    }
    
    console.log('User dashboard initialized for:', state.email);
    console.log('Viewing user:', state.currentViewUserId || 'self');
}

async function fetchUserPhotos() {
    const userId = state.currentViewUserId || state.userId;
    try {
        const photos = await apiFetch(`/screenshots/user/${userId}`);
        renderPhotos(photos);
    } catch (error) {
        console.error('Failed to fetch photos:', error);
        showAlert('Failed to load photos: ' + error.message, 'danger');
    }
}

async function fetchUserEntries() {
    const userId = state.currentViewUserId || state.userId;
    try {
        const entries = await apiFetch(`/users/${userId}/entries`);
        renderEntries(entries);
    } catch (error) {
        console.error('Failed to fetch entries:', error);
        showAlert('Failed to load entries: ' + error.message, 'danger');
    }
}

function renderPhotos(photos) {
    const photosList = document.getElementById('photosList');
    if (!photos || photos.length === 0) {
        photosList.innerHTML = '<p class="text-muted">No photos uploaded yet.</p>';
        return;
    }
    
    photosList.innerHTML = photos.map(photo => `
        <div class="list-group-item d-flex justify-content-between align-items-center photo-item" data-photo-id="${photo.photoId}" data-url="${photo.photoUrl}">
            <img src="${photo.photoUrl}" alt="Screenshot" class="me-3 rounded photo-thumbnail">
            <span class="flex-grow-1 small">${new Date(photo.createdAt).toLocaleString()}</span>
            <div class="action-buttons">
                ${!state.currentViewUserId ? `
                    <button class="btn btn-sm btn-primary generate-btn" data-photo-id="${photo.photoId}">Generate</button>
                    <button class="btn btn-sm btn-danger delete-photo-btn" data-photo-id="${photo.photoId}">Delete</button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function renderEntries(entries) {
    const entriesList = document.getElementById('entriesList');
    const entryCount = document.getElementById('entryCount');
    
    if (entryCount) {
        entryCount.textContent = `${entries.length} entries`;
    }
    
    if (!entries || entries.length === 0) {
        entriesList.innerHTML = '<p class="text-muted">No diary entries yet.</p>';
        return;
    }
    
    entriesList.innerHTML = entries.map(entry => `
        <div class="card mb-3 entry-item" data-entry-id="${entry.entryId}">
            <div class="row g-0">
                <div class="col-md-4">
                    <img src="${entry.imageUrl}" class="img-fluid rounded-start entry-image-clickable" alt="Entry image">
                </div>
                <div class="col-md-8">
                    <div class="card-body">
                        <!-- Content Display -->
                        <div class="content-display" id="content-display-${entry.entryId}">
                            <p class="card-text">${entry.content}</p>
                        </div>
                        
                        <!-- Content Edit Form (Only show for non-admin viewing) -->
                        ${!state.currentViewUserId ? `
                        <div class="content-edit" id="content-edit-${entry.entryId}" style="display: none;">
                            <div class="mb-3">
                                <textarea class="form-control" id="edit-content-${entry.entryId}" rows="4">${entry.content}</textarea>
                            </div>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-success save-entry-btn" data-entry-id="${entry.entryId}">Save</button>
                                <button class="btn btn-secondary cancel-edit-btn" data-entry-id="${entry.entryId}">Cancel</button>
                            </div>
                        </div>
                        ` : ''}
                        
                        <p class="card-text">
                            <small class="text-muted">
                                ${new Date(entry.createdAt).toLocaleString()}
                                ${entry.mode === 'manual' ? '<span class="badge bg-info ms-2">Edited</span>' : ''}
                                ${entry.editedAt ? `<br>Last edited: ${new Date(entry.editedAt).toLocaleString()}` : ''}
                            </small>
                        </p>
                        
                        <!-- Action buttons (Only show for non-admin viewing) -->
                        ${!state.currentViewUserId ? `
                            <div class="action-buttons">
                                <button class="btn btn-sm btn-primary edit-entry-btn" data-entry-id="${entry.entryId}">Edit</button>
                                <button class="btn btn-sm btn-danger delete-entry-btn" data-entry-id="${entry.entryId}">Delete</button>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

async function updateEntry(entryId, content) {
    try {
        const response = await apiFetch(`/users/${state.userId}/entries/${entryId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content })
        });
        showAlert('Entry updated successfully!', 'success');
        return response;
    } catch (error) {
        console.error('Update failed:', error);
        throw error;
    }
}

async function deleteAccount() {
    try {
        await apiFetch(`/users/${state.userId}`, { method: 'DELETE' });
        
        // Clear all local data
        clearAuth();
        
        // Close WebSocket connection
        if (state.ws) {
            state.ws.close();
        }
        
        // Show success message and redirect
        showAlert('Your account and all associated data have been permanently deleted.', 'success');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 2000);
        
    } catch (error) {
        console.error('Account deletion failed:', error);
        showAlert('Failed to delete account. Please try again.', 'danger');
    }
}

function connectUserWebSocket() {
    const ws = connectWebSocket();
    
    if (ws) {
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('🔴 User received real-time update:', message);
            
            const messageUserId = message.userId || (message.data && message.data.userId);
            
            // For admins: only update if viewing the user who made the change
            // For regular users: always update (they can only see their own data)
            const shouldUpdate = state.role === 'admin' 
                ? (state.currentViewUserId === messageUserId || !state.currentViewUserId)
                : true;
            
            if (shouldUpdate) {
                setTimeout(() => {
                    if (message.type === 'photo_created' || message.type === 'photo_deleted') {
                        fetchUserPhotos();
                    }
                    if (message.type === 'entry_created' || message.type === 'entry_deleted' || message.type === 'entry_updated') {
                        fetchUserEntries();
                    }
                }, 2000);
            }
        };
    }
}

function setupUserEventListeners() {
    // Upload form
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const imageFile = document.getElementById('imageFile').files[0];
            const submitBtn = e.target.querySelector('button[type="submit"]');
            
            if (imageFile.size > 10 * 1024 * 1024) {
                showAlert('File too large (max 10MB)', 'warning');
                return;
            }
            
            setLoading(submitBtn, true);
            const formData = new FormData();
            formData.append('image', imageFile);
            formData.append('userId', state.userId);
            
            try {
                await apiFetch('/screenshots/upload', { method: 'POST', body: formData });
                showAlert('Photo uploaded successfully!', 'success');
                e.target.reset();
            } catch (error) {
                console.error('Upload failed:', error);
            } finally {
                setLoading(submitBtn, false, '<i class="bi bi-cloud-upload"></i> Upload to GCS');
            }
        });
    }
    
    // Back button (for admin viewing)
    const backBtn = document.getElementById('backBtn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            window.location.href = 'admin.html';
        });
    }
    
    // Refresh buttons
    const refreshPhotos = document.getElementById('refreshPhotos');
    const refreshEntries = document.getElementById('refreshEntries');
    
    if (refreshPhotos) refreshPhotos.addEventListener('click', fetchUserPhotos);
    if (refreshEntries) refreshEntries.addEventListener('click', fetchUserEntries);
    
    // All click events
    document.addEventListener('click', handleUserClicks);
}

async function handleUserClicks(e) {
    // Photo item clicks (view full image)
    const photoItem = e.target.closest('.photo-item');
    if (photoItem && !e.target.closest('.action-buttons')) {
        const imageUrl = photoItem.dataset.url;
        if (imageUrl) {
            window.open(imageUrl, '_blank');
        }
    }
    
    // Entry image clicks
    if (e.target.classList.contains('entry-image-clickable')) {
        const imageUrl = e.target.src;
        if (imageUrl) {
            window.open(imageUrl, '_blank');
        }
    }
    
    // Generate diary entry
    if (e.target.classList.contains('generate-btn')) {
        const photoId = e.target.dataset.photoId;
        setLoading(e.target, true);
        try {
            await apiFetch(`/screenshots/${photoId}/generate`, { method: 'POST' });
            showAlert('Diary entry generated successfully!', 'success');
        } catch (error) {
            console.error('Generation failed:', error);
        } finally {
            setLoading(e.target, false, 'Generate');
        }
    }
    
    // Delete photo
    if (e.target.classList.contains('delete-photo-btn')) {
        const photoId = e.target.dataset.photoId;
        if (confirm('Delete this photo?')) {
            try {
                await apiFetch(`/screenshots/${photoId}`, { method: 'DELETE' });
                showAlert('Photo deleted successfully', 'info');
            } catch (error) {
                console.error('Delete failed:', error);
            }
        }
    }
    
    // Delete entry
    if (e.target.classList.contains('delete-entry-btn')) {
        const entryId = e.target.dataset.entryId;
        if (confirm('Delete this diary entry?')) {
            try {
                await apiFetch(`/users/${state.userId}/entries/${entryId}`, { method: 'DELETE' });
                showAlert('Entry deleted successfully', 'info');
            } catch (error) {
                console.error('Delete failed:', error);
            }
        }
    }
    
    // Edit entry
    if (e.target.classList.contains('edit-entry-btn')) {
        const entryId = e.target.dataset.entryId;
        const contentDisplay = document.getElementById(`content-display-${entryId}`);
        const contentEdit = document.getElementById(`content-edit-${entryId}`);
        const editBtn = e.target;
        
        // Hide display, show edit form
        contentDisplay.style.display = 'none';
        contentEdit.style.display = 'block';
        editBtn.style.display = 'none';
    }
    
    // Cancel edit
    if (e.target.classList.contains('cancel-edit-btn')) {
        const entryId = e.target.dataset.entryId;
        const contentDisplay = document.getElementById(`content-display-${entryId}`);
        const contentEdit = document.getElementById(`content-edit-${entryId}`);
        const editBtn = document.querySelector(`[data-entry-id="${entryId}"].edit-entry-btn`);
        
        // Show display, hide edit form
        contentDisplay.style.display = 'block';
        contentEdit.style.display = 'none';
        editBtn.style.display = 'inline-block';
        
        // Reset textarea to original content
        const originalContent = contentDisplay.querySelector('p').textContent;
        document.getElementById(`edit-content-${entryId}`).value = originalContent;
    }
    
    // Save entry
    if (e.target.classList.contains('save-entry-btn')) {
        const entryId = e.target.dataset.entryId;
        const textarea = document.getElementById(`edit-content-${entryId}`);
        const newContent = textarea.value.trim();
        
        if (!newContent) {
            showAlert('Content cannot be empty', 'warning');
            return;
        }
        
        const saveBtn = e.target;
        setLoading(saveBtn, true);
        
        try {
            await updateEntry(entryId, newContent);
            
            // Update the display content
            const contentDisplay = document.getElementById(`content-display-${entryId}`);
            const contentEdit = document.getElementById(`content-edit-${entryId}`);
            const editBtn = document.querySelector(`[data-entry-id="${entryId}"].edit-entry-btn`);
            
            contentDisplay.querySelector('p').textContent = newContent;
            contentDisplay.style.display = 'block';
            contentEdit.style.display = 'none';
            editBtn.style.display = 'inline-block';
            
        } catch (error) {
            console.error('Save failed:', error);
        } finally {
            setLoading(saveBtn, false, 'Save');
        }
    }
    
    // Delete account
    if (e.target.id === 'deleteAccountBtn') {
        const userEmail = state.email;
        const confirmMessage = `⚠️ WARNING: This action cannot be undone!\n\nThis will permanently delete:\n- Your account (${userEmail})\n- All your photos\n- All your diary entries\n- All associated data\n\nType "DELETE" to confirm:`;
        
        const userInput = prompt(confirmMessage);
        
        if (userInput === 'DELETE') {
            const finalConfirm = confirm(`Are you absolutely sure you want to delete your account "${userEmail}"?\n\nThis action is PERMANENT and cannot be reversed.`);
            
            if (finalConfirm) {
                deleteAccount();
            }
        } else if (userInput !== null) {
            showAlert('Account deletion cancelled. You must type "DELETE" exactly.', 'warning');
        }
    }
}