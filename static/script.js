let refreshInterval;
let isRefreshing = false;

const downloadForm = document.getElementById('downloadForm');
const urlInput = document.getElementById('urlInput');
const downloadBtn = document.getElementById('downloadBtn');
const downloadBtnText = document.getElementById('downloadBtnText');
const downloadBtnSpinner = document.getElementById('downloadBtnSpinner');
const bulkToggleBtn = document.getElementById('bulkToggleBtn');
const bulkPanel = document.getElementById('bulkPanel');
const bulkDownloadBtn = document.getElementById('bulkDownloadBtn');
const previewBtn = document.getElementById('previewBtn');
const urlsTextarea = document.getElementById('urls');
const refreshBtn = document.getElementById('refreshBtn');
const jobsList = document.getElementById('jobsList');
const previewModal = document.getElementById('previewModal');
const previewContent = document.getElementById('previewContent');
const closeModal = document.getElementById('closeModal');
const toastContainer = document.getElementById('toastContainer');

document.addEventListener('DOMContentLoaded', function() {
  setupEventListeners();
  refreshStatus();
  startAutoRefresh();
});

function setupEventListeners() {
  downloadForm.addEventListener('submit', handleSingleDownload);
  bulkToggleBtn.addEventListener('click', toggleBulkPanel);
  bulkDownloadBtn.addEventListener('click', handleBulkDownload);
  previewBtn.addEventListener('click', handlePreview);
  refreshBtn.addEventListener('click', refreshStatus);
  closeModal.addEventListener('click', hidePreviewModal);

  previewModal.addEventListener('click', function(e) {
    if (e.target === previewModal) hidePreviewModal();
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && previewModal.style.display !== 'none') {
      hidePreviewModal();
    }
  });

  urlInput.addEventListener('paste', function(e) {
    setTimeout(() => {
      const val = urlInput.value;
      if (val.includes('\n')) {
        urlsTextarea.value = val;
        urlInput.value = '';
        bulkPanel.style.display = 'block';
        bulkToggleBtn.textContent = '- Bulk Add';
        urlsTextarea.focus();
      }
    }, 0);
  });
}

async function handleSingleDownload(e) {
  e.preventDefault();
  const url = urlInput.value.trim();
  if (!url || (!url.startsWith('http://') && !url.startsWith('https://'))) {
    showToast('Please enter a valid URL', 'error');
    return;
  }

  setDownloadButtonLoading(true);
  try {
    const response = await fetch('/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urls: [url] }),
    });
    const data = await response.json();
    if (response.ok) {
      showToast('Download queued', 'success');
      urlInput.value = '';
      refreshStatus();
    } else {
      showToast(data.error || 'Failed to queue download', 'error');
    }
  } catch (error) {
    showToast('Network error', 'error');
  } finally {
    setDownloadButtonLoading(false);
    urlInput.focus();
  }
}

async function handleBulkDownload() {
  const urls = getUrlsFromTextarea();
  if (urls.length === 0) {
    showToast('No valid URLs found', 'error');
    return;
  }

  bulkDownloadBtn.disabled = true;
  try {
    const response = await fetch('/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urls }),
    });
    const data = await response.json();
    if (response.ok) {
      showToast(`Queued ${data.new_count} downloads`, 'success');
      urlsTextarea.value = '';
      refreshStatus();
    } else {
      showToast(data.error || 'Failed to queue downloads', 'error');
    }
  } catch (error) {
    showToast('Network error', 'error');
  } finally {
    bulkDownloadBtn.disabled = false;
  }
}

function toggleBulkPanel() {
  const visible = bulkPanel.style.display !== 'none';
  bulkPanel.style.display = visible ? 'none' : 'block';
  bulkToggleBtn.textContent = visible ? '+ Bulk Add' : '- Bulk Add';
}

async function handlePreview() {
  const urls = getUrlsFromTextarea();
  if (urls.length === 0) {
    showToast('Enter URLs in the bulk panel first', 'error');
    return;
  }

  previewBtn.disabled = true;
  previewBtn.textContent = 'Loading...';

  try {
    const previews = [];
    for (const url of urls.slice(0, 5)) {
      try {
        const response = await fetch('/info', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
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
  } finally {
    previewBtn.disabled = false;
    previewBtn.textContent = 'Preview Info';
  }
}

function getUrlsFromTextarea() {
  return urlsTextarea.value
    .split('\n')
    .map(url => url.trim())
    .filter(url => url && (url.startsWith('http://') || url.startsWith('https://')));
}

function setDownloadButtonLoading(loading) {
  downloadBtn.disabled = loading;
  downloadBtnText.style.display = loading ? 'none' : 'inline';
  downloadBtnSpinner.style.display = loading ? 'inline' : 'none';
}

async function refreshStatus() {
  if (isRefreshing) return;
  isRefreshing = true;

  try {
    const response = await fetch('/status');
    const data = await response.json();
    if (response.ok) {
      updateJobsList(data.jobs);
    }
  } catch (error) {
    // silent
  } finally {
    isRefreshing = false;
  }
}

function updateJobsList(jobs) {
  if (!jobs || jobs.length === 0) {
    jobsList.innerHTML = '<div class="no-jobs">No downloads yet. Paste a URL above to get started.</div>';
    return;
  }

  const now = Date.now();
  const thirtySeconds = 30 * 1000;

  const active = [];
  const recent = [];

  for (const job of jobs) {
    if (job.status === 'queued' || job.status === 'downloading') {
      active.push(job);
    } else if (job.completed_at) {
      const completedAge = now - new Date(job.completed_at).getTime();
      if (completedAge < thirtySeconds) {
        active.push(job);
      } else {
        recent.push(job);
      }
    } else {
      active.push(job);
    }
  }

  active.sort((a, b) => new Date(b.started_at) - new Date(a.started_at));
  recent.sort((a, b) => new Date(b.completed_at) - new Date(a.completed_at));

  let html = '';

  if (active.length > 0) {
    html += active.map(job => createJobItemHTML(job)).join('');
  } else if (recent.length > 0) {
    html += '<div class="no-jobs">All downloads complete.</div>';
  } else {
    html += '<div class="no-jobs">No downloads yet. Paste a URL above to get started.</div>';
  }

  if (recent.length > 0) {
    const shown = recent.slice(0, 10);
    html += `
      <div class="recent-section">
        <div class="recent-header" onclick="toggleRecent()">
          <span>Recent (${recent.length})</span>
          <span id="recentToggle" class="recent-toggle">▸</span>
        </div>
        <div id="recentList" class="recent-list" style="display: none;">
          ${shown.map(job => createJobItemHTML(job)).join('')}
        </div>
      </div>`;
  }

  jobsList.innerHTML = html;
}

function toggleRecent() {
  const list = document.getElementById('recentList');
  const toggle = document.getElementById('recentToggle');
  if (list.style.display === 'none') {
    list.style.display = 'block';
    toggle.textContent = '▾';
  } else {
    list.style.display = 'none';
    toggle.textContent = '▸';
  }
}

function createJobItemHTML(job) {
  const progress = Math.max(0, Math.min(100, job.progress || 0));
  const statusClass = `status-${job.status}`;
  const statusText = job.status.charAt(0).toUpperCase() + job.status.slice(1);

  let progressHTML = '';
  if (job.status === 'queued') {
    progressHTML = `
      <div class="job-progress">
        <div class="progress-bar">
          <div class="progress-fill indeterminate"></div>
        </div>
        <div class="progress-text">Waiting...</div>
      </div>`;
  } else if (job.status === 'downloading') {
    const speedText = job.speed ? formatSpeed(job.speed) : '';
    const etaText = job.eta ? formatETA(job.eta) : '';
    const details = [
      `${progress}%`,
      speedText,
      etaText ? `ETA: ${etaText}` : '',
    ].filter(Boolean).join('  ·  ');

    progressHTML = `
      <div class="job-progress">
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${progress}%"></div>
        </div>
        <div class="progress-text">${details}</div>
      </div>`;
  } else if (job.status === 'completed') {
    progressHTML = `
      <div class="job-progress">
        <div class="progress-bar">
          <div class="progress-fill completed" style="width: 100%"></div>
        </div>
      </div>`;
  }

  let detailsHTML = '';
  if (job.filename) {
    detailsHTML += `<div class="job-detail"><span class="job-filename">${escapeHtml(job.filename)}</span></div>`;
  }
  if (job.error && job.status === 'failed') {
    detailsHTML += `<div class="job-detail job-error">${escapeHtml(job.error)}</div>`;
  }

  return `
    <div class="job-item ${statusClass}">
      <div class="job-header">
        <div class="job-url">${escapeHtml(truncateUrl(job.url))}</div>
        <div class="job-status-badge ${statusClass}">${statusText}</div>
      </div>
      ${progressHTML}
      ${detailsHTML ? `<div class="job-details">${detailsHTML}</div>` : ''}
    </div>`;
}

function showPreviewModal(previews) {
  const content = previews.map(preview => {
    if (preview.error) {
      return `
        <div class="preview-item">
          <div class="preview-title">${escapeHtml(preview.url)}</div>
          <div class="preview-error">Error: ${escapeHtml(preview.error)}</div>
        </div>`;
    }
    const info = preview.info;
    return `
      <div class="preview-item">
        <div class="preview-title">${escapeHtml(info.title)}</div>
        <div class="preview-details">
          <span>${escapeHtml(info.uploader)}</span>
          <span>${info.duration ? formatDuration(info.duration) : ''}</span>
          <span>${info.view_count ? formatNumber(info.view_count) + ' views' : ''}</span>
        </div>
      </div>`;
  }).join('');

  previewContent.innerHTML = content;
  previewModal.style.display = 'flex';
}

function hidePreviewModal() {
  previewModal.style.display = 'none';
}

function startAutoRefresh() {
  refreshInterval = setInterval(() => {
    if (!isRefreshing) refreshStatus();
  }, 2000);
}

function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);

  setTimeout(() => toast.classList.add('show'), 50);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 300);
  }, 4000);
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function truncateUrl(url) {
  if (!url) return '';
  if (url.length <= 80) return url;
  return url.substring(0, 77) + '...';
}

function formatSpeed(bytesPerSec) {
  if (!bytesPerSec || bytesPerSec <= 0) return '';
  if (bytesPerSec >= 1048576) return (bytesPerSec / 1048576).toFixed(1) + ' MB/s';
  if (bytesPerSec >= 1024) return (bytesPerSec / 1024).toFixed(0) + ' KB/s';
  return bytesPerSec.toFixed(0) + ' B/s';
}

function formatETA(seconds) {
  if (!seconds || seconds <= 0) return '';
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}:${m.toString().padStart(2, '0')}:00`;
  }
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDuration(seconds) {
  if (!seconds) return '';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatNumber(num) {
  if (!num) return '';
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

document.addEventListener('visibilitychange', function() {
  if (document.hidden) {
    stopAutoRefresh();
  } else {
    startAutoRefresh();
    refreshStatus();
  }
});
