/**
 * Leopa Color - Upload and Colorization JavaScript
 */

// State
let selectedReferences = new Set();
let currentJobId = null;
let pollingInterval = null;

/**
 * Initialize the application
 */
function init() {
    setupDropZones();
    setupReferenceSelection();
    setupColorizeForm();
}

/**
 * Setup drag and drop zones
 */
function setupDropZones() {
    // Reference image drop zone
    const refDropZone = document.getElementById('reference-drop-zone');
    if (refDropZone) {
        setupDropZone(refDropZone, handleReferenceUpload);
    }

    // Infrared image drop zone
    const irDropZone = document.getElementById('infrared-drop-zone');
    if (irDropZone) {
        setupDropZone(irDropZone, handleInfraredUpload);
    }
}

/**
 * Setup a drop zone element
 */
function setupDropZone(element, uploadHandler) {
    const fileInput = element.querySelector('input[type="file"]');

    // Click to select file
    element.addEventListener('click', (e) => {
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        const files = e.target.files;
        if (files.length > 0) {
            uploadHandler(files[0]);
        }
        // Reset input so same file can be selected again
        fileInput.value = '';
    });

    // Drag events
    element.addEventListener('dragover', (e) => {
        e.preventDefault();
        element.classList.add('dragover');
    });

    element.addEventListener('dragleave', (e) => {
        e.preventDefault();
        element.classList.remove('dragover');
    });

    element.addEventListener('drop', (e) => {
        e.preventDefault();
        element.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadHandler(files[0]);
        }
    });
}

/**
 * Handle reference image upload
 */
async function handleReferenceUpload(file) {
    if (!validateImageFile(file)) {
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/references', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        showNotification('Reference image uploaded successfully', 'success');
        // Reload the reference list
        location.reload();
    } catch (error) {
        showNotification(`Upload failed: ${error.message}`, 'error');
    }
}

/**
 * Handle infrared image selection for colorization
 */
function handleInfraredUpload(file) {
    if (!validateImageFile(file)) {
        return;
    }

    // Store file for later submission
    window.selectedInfraredFile = file;

    // Show preview
    const preview = document.getElementById('infrared-preview');
    if (preview) {
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.innerHTML = `
                <div class="result-image-container">
                    <h3>Selected Infrared Image</h3>
                    <img src="${e.target.result}" alt="Infrared image">
                </div>
            `;
        };
        reader.readAsDataURL(file);
    }

    // Enable colorize button if references are selected
    updateColorizeButton();
}

/**
 * Validate image file
 */
function validateImageFile(file) {
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        showNotification('Invalid file type. Please upload JPEG, PNG, GIF, or WebP.', 'error');
        return false;
    }

    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        showNotification('File too large. Maximum size is 10MB.', 'error');
        return false;
    }

    return true;
}

/**
 * Setup reference image selection
 */
function setupReferenceSelection() {
    const referenceItems = document.querySelectorAll('.reference-item');

    referenceItems.forEach((item) => {
        const refId = item.dataset.refId;

        // Click to select/deselect
        item.addEventListener('click', (e) => {
            // Don't toggle if clicking delete button
            if (e.target.closest('.delete-btn')) {
                return;
            }

            if (selectedReferences.has(refId)) {
                selectedReferences.delete(refId);
                item.classList.remove('selected');
            } else {
                selectedReferences.add(refId);
                item.classList.add('selected');
            }

            updateColorizeButton();
        });

        // Delete button
        const deleteBtn = item.querySelector('.delete-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                await deleteReference(refId);
            });
        }
    });
}

/**
 * Delete a reference image
 */
async function deleteReference(refId) {
    if (!confirm('Delete this reference image?')) {
        return;
    }

    try {
        const response = await fetch(`/api/references/${refId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error('Delete failed');
        }

        showNotification('Reference image deleted', 'success');
        selectedReferences.delete(refId);
        location.reload();
    } catch (error) {
        showNotification(`Delete failed: ${error.message}`, 'error');
    }
}

/**
 * Update colorize button state
 */
function updateColorizeButton() {
    const btn = document.getElementById('colorize-btn');
    if (btn) {
        const hasFile = window.selectedInfraredFile != null;
        const hasRefs = selectedReferences.size > 0;
        btn.disabled = !hasFile || !hasRefs;
    }
}

/**
 * Setup colorize form
 */
function setupColorizeForm() {
    const form = document.getElementById('colorize-form');
    if (form) {
        form.addEventListener('submit', handleColorizeSubmit);
    }
}

/**
 * Handle colorize form submission
 */
async function handleColorizeSubmit(e) {
    e.preventDefault();

    if (!window.selectedInfraredFile) {
        showNotification('Please select an infrared image', 'error');
        return;
    }

    if (selectedReferences.size === 0) {
        showNotification('Please select at least one reference image', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', window.selectedInfraredFile);
    formData.append('reference_ids', Array.from(selectedReferences).join(','));

    // Show processing status
    showStatus('processing', 'Starting colorization...');

    try {
        const response = await fetch('/api/colorize', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Colorization failed');
        }

        const data = await response.json();
        currentJobId = data.job_id;

        // Start polling for status
        startPolling();
    } catch (error) {
        showStatus('error', `Colorization failed: ${error.message}`);
    }
}

/**
 * Start polling for job status
 */
function startPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }

    pollingInterval = setInterval(checkJobStatus, 2000);
}

/**
 * Check job status
 */
async function checkJobStatus() {
    if (!currentJobId) {
        clearInterval(pollingInterval);
        return;
    }

    try {
        const response = await fetch(`/api/colorize/${currentJobId}`);
        if (!response.ok) {
            throw new Error('Failed to check status');
        }

        const data = await response.json();

        switch (data.status) {
            case 'pending':
                showStatus('processing', 'Waiting to start...');
                break;
            case 'processing':
                showStatus('processing', 'Colorizing image...');
                break;
            case 'completed':
                clearInterval(pollingInterval);
                showStatus('success', 'Colorization complete!');
                showResult(data.result_url);
                break;
            case 'failed':
                clearInterval(pollingInterval);
                showStatus('error', `Failed: ${data.error_message || 'Unknown error'}`);
                break;
        }
    } catch (error) {
        clearInterval(pollingInterval);
        showStatus('error', `Error checking status: ${error.message}`);
    }
}

/**
 * Show status message
 */
function showStatus(type, message) {
    const container = document.getElementById('status-container');
    if (!container) return;

    let icon = '';
    switch (type) {
        case 'processing':
            icon = '<div class="spinner"></div>';
            break;
        case 'success':
            icon = '<span style="color: var(--success-color); font-size: 24px;">&#10003;</span>';
            break;
        case 'error':
            icon = '<span style="color: var(--error-color); font-size: 24px;">&#10005;</span>';
            break;
    }

    container.innerHTML = `
        <div class="status-message ${type}">
            ${icon}
            <span>${message}</span>
        </div>
    `;
}

/**
 * Show colorization result
 */
function showResult(resultUrl) {
    const container = document.getElementById('result-container');
    if (!container) return;

    // Get infrared preview
    const infraredImg = document.querySelector('#infrared-preview img');
    const infraredSrc = infraredImg ? infraredImg.src : '';

    container.innerHTML = `
        <div class="result-comparison">
            <div class="result-image-container">
                <h3>Original (Infrared)</h3>
                <img src="${infraredSrc}" alt="Original infrared image">
            </div>
            <div class="result-image-container">
                <h3>Colorized Result</h3>
                <img src="${resultUrl}" alt="Colorized image">
            </div>
        </div>
        <div class="result-actions">
            <a href="${resultUrl}" download class="btn btn-success">Download Result</a>
            <button type="button" class="btn btn-secondary" onclick="resetForm()">Colorize Another</button>
        </div>
    `;
}

/**
 * Reset form for another colorization
 */
function resetForm() {
    window.selectedInfraredFile = null;
    currentJobId = null;

    const preview = document.getElementById('infrared-preview');
    if (preview) preview.innerHTML = '';

    const status = document.getElementById('status-container');
    if (status) status.innerHTML = '';

    const result = document.getElementById('result-container');
    if (result) result.innerHTML = '';

    updateColorizeButton();
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
