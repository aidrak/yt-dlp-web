// Global state
let refreshInterval;
let isRefreshing = false;

// DOM elements
const downloadForm = document.getElementById('downloadForm');
const urlsTextarea = document.getElementById('urls');
const downloadBtn = document.getElementById('downloadBtn');
const downloadBtnText = document.getElementById('downloadBtnText');
const downloadBtnSpinner = document.getElementById('downloadBtnSpinner');
const previewBtn = document.getElementById('previewBtn');
const clearBtn = document.getElementById('clearBtn');
const refreshBtn = document.getElementById('refreshBtn');
const jobsList = document.getElementById('jobsList');
const previewModal = document.getElementById('previewModal');
const previewContent = document.getElementById('previewContent');
const closeModal = document.getElementById('closeModal');
const toastContainer = document.getElementById('toastContainer');

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    refreshStatus();
    startAutoRefresh();
});

// Event listeners
function setupEventListeners() {
    downloadForm.addEventListener('submit', handleDownload);
    previewBtn.addEventListener('click', handlePreview);
    clearBtn.addEventListener('click', handleClear);
    refreshBtn.addEventListener('click', refreshStatus);
    closeModal.addEventListener('click', hidePreviewModal);

    // Close modal when clicking outside
    previewModal.addEventListener('click', function(e) {
        if (e.target === previewModal) {
            hidePreviewModal();
        }
    });

    // ESC key to close modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && previewModal.style.display !== 'none') {
            hidePreviewModal();
        }
    });

    // Auto-expand textarea
    urlsTextarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.max(this.scrollHeight, 120) + 'px';
    });
}

// Handle download form submission
async function handleDownload(e) {
    e.preventDefault();

    const urls = getUrlsFromTextarea();
    if (urls.length === 0) {
        showToast('Please enter at least one valid URL', 'error');
        return;
    }

    setDownloadButtonLoading(true);

    try {
        const response = await fetch('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ urls }),
        });

        const data = await response.json();

        if (response.ok) {
            showToast(`Successfully queued ${data.job_ids.length} downloads`, 'success');
            urlsTextarea.value = '';
            urlsTextarea.style.height = 'auto';
            refreshStatus();
        } else {
            showToast(data.error || 'Failed to start downloads', 'error');
        }
    } catch (error) {
        console.error('Download error:', error);
        showToast('Network error occurred', 'error');
    } finally {
        setDownloadButtonLoading(false);
    }
}

// Handle preview
async function handlePreview() {
    const urls = getUrlsFromTextarea();
    if (urls.length === 0) {
        showToast('Please enter at least one valid URL', 'error');
        return;
    }

    previewBtn.disabled = true;
    previewBtn.innerHTML = '⏳ Loading...';

    try {
        const previews = [];

        for (const url of urls.slice(0, 5)) { // Limit to 5 URLs for preview
            try {
                const response = await fetch('/info', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url }),
                });

                const data = await response.json();

                if (response.ok) {
                    previews.push({ url, info: data.info });
                } else {
                    previews.push({ url, error: data.error });
                }
            } catch (error) {
                previews.push({ url, error: 'Network error' });
            }
        }

        showPreviewModal(previews);
    } catch (error) {
        console.error('Preview error:', error);
        showToast('Failed to load preview', 'error');
    } finally {
        previewBtn.disabled = false;
        previewBtn.innerHTML = '👁️ Preview Info';
    }
}

// Handle clear
function handleClear() {
    if (urlsTextarea.value.trim() === '') return;

    if (confirm('Are you sure you want to clear all URLs?')) {
        urlsTextarea.value = '';
        urlsTextarea.style.height = 'auto';
        urlsTextarea.focus();
    }
}

// Get URLs from textarea
function getUrlsFromTextarea() {
    return urlsTextarea.value
        .split('\n')
        .map(url => url.trim())
        .filter(url => url && (url.startsWith('http://') || url.startsWith('https://')));
}

// Set download button loading state
function setDownloadButtonLoading(loading) {
    downloadBtn.disabled = loading;
    if (loading) {
        downloadBtnText.style.display = 'none';
        downloadBtnSpinner.style.display = 'inline';
    } else {
        downloadBtnText.style.display = 'inline';
        downloadBtnSpinner.style.display = 'none';
    }
}

// Refresh status
async function refreshStatus() {
    if (isRefreshing) return;

    isRefreshing = true;
    refreshBtn.disabled = true;
    refreshBtn.innerHTML = '⏳ Refreshing...';

    try {
        const response = await fetch('/status');
        const data = await response.json();

        if (response.ok) {
            updateJobsList(data.jobs);
        } else {
            console.error('Failed to fetch status:', data.error);
        }
    } catch (error) {
        console.error('Status refresh error:', error);
    } finally {
        isRefreshing = false;
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '🔄 Refresh';
    }
}

// Update jobs list
function updateJobsList(jobs) {
    if (!jobs || jobs.length === 0) {
        jobsList.innerHTML = '<div class="no-jobs">No downloads yet. Add some URLs above to get started!</div>';
        return;
    }

    // Sort jobs by started time (newest first)
    jobs.sort((a, b) => new Date(b.started_at) - new Date(a.started_at));

    jobsList.innerHTML = jobs.map(job => createJobItemHTML(job)).join('');
}

// Create job item HTML
function createJobItemHTML(job) {
    const progress = Math.max(0, Math.min(100, job.progress || 0));
    const statusClass = `status-${job.status}`;
    const statusText = job.status.charAt(0).toUpperCase() + job.status.slice(1);

    return `
        <div class="job-item">
            <div class="job-header">
                <div class="job-url">${escapeHtml(job.url)}</div>
                <div class="job-status ${statusClass}">${statusText}</div>
            </div>

            ${job.status === 'downloading' ? `
                <div class="job-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <div class="progress-text">${progress}% complete</div>
                </div>
            ` : ''}

            <div class="job-details">
                <div class="job-detail">
                    <span>📅</span>
                    <span>${formatDateTime(job.started_at)}</span>
                </div>

                ${job.filename ? `
                    <div class="job-detail">
                        <span>📁</span>
                        <span class="job-filename">${escapeHtml(job.filename)}</span>
                    </div>
                ` : ''}

                ${job.completed_at && job.status === 'completed' ? `
                    <div class="job-detail">
                        <span>✅</span>
                        <span>Completed ${formatDateTime(job.completed_at)}</span>
                    </div>
                ` : ''}

                ${job.error ? `
                    <div class="job-detail">
                        <span>❌</span>
                        <span class="job-error">${escapeHtml(job.error)}</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

// Show preview modal
function showPreviewModal(previews) {
    const content = previews.map(preview => {
        if (preview.error) {
            return `
                <div class="preview-item">
                    <div class="preview-title">❌ ${escapeHtml(preview.url)}</div>
                    <div style="color: #e53e3e;">Error: ${escapeHtml(preview.error)}</div>
                </div>
            `;
        }

        const info = preview.info;
        const duration = info.duration ? formatDuration(info.duration) : 'Unknown';
        const views = info.view_count ? formatNumber(info.view_count) : 'Unknown';

        return `
            <div class="preview-item">
                <div class="preview-title">📹 ${escapeHtml(info.title)}</div>
                <div class="preview-details">
                    <div><strong>Channel:</strong> ${escapeHtml(info.uploader)}</div>
                    <div><strong>Duration:</strong> ${duration}</div>
                    <div><strong>Views:</strong> ${views}</div>
                    <div><strong>Upload Date:</strong> ${formatUploadDate(info.upload_date)}</div>
                </div>
            </div>
        `;
    }).join('');

    previewContent.innerHTML = content;
    previewModal.style.display = 'flex';
}

// Hide preview modal
function hidePreviewModal() {
    previewModal.style.display = 'none';
}

// Start auto refresh
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        if (!isRefreshing) {
            refreshStatus();
        }
    }, 3000); // Refresh every 3 seconds
}

// Stop auto refresh
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    toastContainer.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 100);

    // Remove toast after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 5000);
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDateTime(isoString) {
    if (!isoString) return 'Unknown';

    const date = new Date(isoString);
    return date.toLocaleString();
}

function formatDuration(seconds) {
    if (!seconds) return 'Unknown';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
}

function formatNumber(num) {
    if (!num) return 'Unknown';

    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    } else {
        return num.toString();
    }
}

function formatUploadDate(dateString) {
    if (!dateString || dateString.length < 8) return 'Unknown';

    const year = dateString.substring(0, 4);
    const month = dateString.substring(4, 6);
    const day = dateString.substring(6, 8);

    return `${year}-${month}-${day}`;
}

// Handle page visibility change to pause/resume auto refresh
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        startAutoRefresh();
        refreshStatus();
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});