const DEFAULT_HINT = 'Paste a URL and the studio will queue the job instantly.';

import { wsNotifier } from '/static/js/ws-status.js';

const elements = {
    urlInput: document.getElementById('youtube-url'),
    formatRadios: document.querySelectorAll("input[name='format']"),
    downloadBtn: document.getElementById('download-btn'),
    statusMessage: document.getElementById('status-message'),
    formHint: document.getElementById('form-hint'),
    metadataCard: document.getElementById('metadata-card'),
    thumbnail: document.getElementById('track-thumbnail'),
    trackTitle: document.getElementById('track-title'),
    trackAuthor: document.getElementById('track-author'),
    progressCard: document.getElementById('progress-card'),
    progressFill: document.getElementById('progress-fill'),
    progressPercentage: document.getElementById('progress-percentage'),
    progressBytes: document.getElementById('progress-bytes'),
    history: document.getElementById('history'),
    historyEmpty: document.getElementById('history-empty'),
    speedLabel: document.getElementById('progress-speed'),
    phaseLabel: document.getElementById('progress-phase'),
    cancelButton: document.getElementById('progress-cancel'),
};

const state = {
    ws: null,
    reconnectTimer: null,
    pendingPayload: null,
    totalBytes: 0,
    downloadedBytes: 0,
    currentTrack: null,
    currentFormat: 'mp4',
    lastUpdateTime: 0,
    lastProgressBytes: 0,
};

const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/youtube/download_track`;
const notify = wsNotifier('YouTube');

function setStatusMessage(message) {
    elements.statusMessage.textContent = message;
}

function setHint(message, tone = 'muted') {
    elements.formHint.textContent = message;
    elements.formHint.classList.remove('error');
    if (tone === 'error') {
        elements.formHint.classList.add('error');
    }
}

function setBusy(isBusy) {
    elements.downloadBtn.disabled = isBusy;
    elements.downloadBtn.textContent = isBusy ? 'Working…' : 'Download';
}

function finishTransfer(statusMessage = 'Ready for another URL', hintMessage = DEFAULT_HINT) {
    setBusy(false);
    setStatusMessage(statusMessage);
    resetProgress();
    hideMetadata();
    setHint(hintMessage);
}

function showMetadata(track) {
    elements.metadataCard.classList.remove('hidden');
    elements.thumbnail.src = track.thumbnail_url || '';
    elements.trackTitle.textContent = track.title || 'Unknown title';
    elements.trackAuthor.textContent = track.author || 'Unknown author';
}

function hideMetadata() {
    elements.metadataCard.classList.add('hidden');
    elements.trackTitle.textContent = '--';
    elements.trackAuthor.textContent = '--';
    elements.thumbnail.src = '';
}

function resetProgress() {
    state.downloadedBytes = 0;
    state.totalBytes = 0;
    elements.progressFill.style.width = '0%';
    elements.progressPercentage.textContent = '0%';
    elements.progressBytes.textContent = '0 / 0';
    elements.phaseLabel.textContent = 'Idle';
    elements.speedLabel.textContent = '--';
    elements.progressCard.classList.add('hidden');
    state.lastUpdateTime = 0;
    state.lastProgressBytes = 0;
}

function updateProgress(bytes, total) {
    elements.progressCard.classList.remove('hidden');
    if (!total) {
        elements.progressFill.style.width = '100%';
        elements.progressPercentage.textContent = '--';
        elements.progressBytes.textContent = 'Streaming…';
        return;
    }
    const percentage = Math.min(100, (bytes / total) * 100);
    elements.progressFill.style.width = `${percentage}%`;
    elements.progressPercentage.textContent = `${percentage.toFixed(1)}%`;

    const formatBytes = (value) =>
        value > 1024 * 1024
            ? `${(value / (1024 * 1024)).toFixed(1)} MB`
            : `${(value / 1024).toFixed(1)} KB`;
    elements.progressBytes.textContent = `${formatBytes(bytes)} / ${formatBytes(total)}`;

    const now = performance.now();
    if (state.lastUpdateTime) {
        const deltaBytes = bytes - state.lastProgressBytes;
        const deltaTime = (now - state.lastUpdateTime) / 1000;
        if (deltaTime > 0 && deltaBytes >= 0) {
            const speed = deltaBytes / deltaTime;
            elements.speedLabel.textContent =
                speed > 1024 * 1024 ? `${(speed / 1024 / 1024).toFixed(2)} MB/s` : `${(speed / 1024).toFixed(1)} KB/s`;
        }
    }
    state.lastUpdateTime = now;
    state.lastProgressBytes = bytes;
}

function addHistoryItem(track, url, filename, format) {
    elements.historyEmpty?.remove();
    const card = document.createElement('article');
    card.className = 'history-item';
    card.innerHTML = `
        <div class="history-thumb">
            <img src="${track?.thumbnail_url || ''}" alt="Thumbnail">
        </div>
        <div class="history-details">
            <span class="chip">${format.toUpperCase()}</span>
            <p class="history-headline">${track?.title || filename}</p>
            <p class="muted">${track?.author || 'Unknown source'}</p>
            <div class="history-actions">
                <button type="button" class="ghost-button history-download">Download</button>
            </div>
        </div>
    `;
    card.querySelector('.history-download').addEventListener('click', () => triggerDownload(url, filename));
    elements.history.prepend(card);
}

function triggerDownload(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function connectWebSocket() {
    if (state.ws && (state.ws.readyState === WebSocket.OPEN || state.ws.readyState === WebSocket.CONNECTING)) {
        return;
    }

    notify.connecting();
    state.ws = new WebSocket(wsUrl);

    state.ws.addEventListener('open', () => {
        notify.connected();
        if (state.pendingPayload) {
            state.ws.send(JSON.stringify(state.pendingPayload));
            state.pendingPayload = null;
        }
    });

    state.ws.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    });

    state.ws.addEventListener('close', () => {
        notify.disconnected();
        if (elements.downloadBtn.disabled) {
            finishTransfer('Connection lost. Reconnecting…', 'Connection dropped—please retry once reconnected.');
        }
        if (!state.reconnectTimer) {
            state.reconnectTimer = setTimeout(() => {
                state.reconnectTimer = null;
                connectWebSocket();
            }, 1500);
        }
    });

    state.ws.addEventListener('error', () => {
        notify.error();
        if (elements.downloadBtn.disabled) {
            finishTransfer('Connection error', 'Connection error—try again in a moment.');
        }
    });
}

function sendDownloadRequest(payload) {
    state.currentFormat = payload.format;
    state.currentTrack = null;
    resetProgress();
    hideMetadata();
    setBusy(true);
    setHint('Queuing job…');

    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify(payload));
    } else {
        state.pendingPayload = payload;
        connectWebSocket();
    }
}

function handleMessage(message) {
    switch (message.type) {
        case 'metadata':
            state.currentTrack = message;
            showMetadata(message);
            setStatusMessage('Metadata resolved');
            break;
        case 'downloader_start':
            state.totalBytes = message.total || 0;
            state.downloadedBytes = 0;
            updateProgress(0, state.totalBytes);
            elements.phaseLabel.textContent = 'Downloading';
            setStatusMessage('Starting transfer…');
            break;
        case 'downloader_update':
            state.downloadedBytes += message.progress || 0;
            updateProgress(state.downloadedBytes, state.totalBytes);
            break;
        case 'downloader_end':
            updateProgress(state.totalBytes, state.totalBytes);
            elements.phaseLabel.textContent = 'Finishing';
            break;
        case 'info':
            setStatusMessage(message.info_message || '');
            if (message.info_message?.toLowerCase().includes('extracting mp3')) {
                elements.phaseLabel.textContent = 'Converting to MP3';
            }
            break;
        case 'file_ready':
            if (state.currentTrack) {
                addHistoryItem(state.currentTrack, message.url, message.filename, message.format || state.currentFormat);
            }
            triggerDownload(message.url, message.filename);
            break;
        case 'completed':
            finishTransfer('Ready for another URL');
            break;
        default:
            console.debug('Unhandled message', message);
    }
}

elements.downloadBtn.addEventListener('click', () => {
    const youtubeUrl = elements.urlInput.value.trim();
    if (!youtubeUrl) {
        setHint('Paste a valid YouTube link first.', 'error');
        return;
    }

    const selectedFormat = Array.from(elements.formatRadios).find((radio) => radio.checked)?.value || 'mp4';
    sendDownloadRequest({ youtube_url: youtubeUrl, format: selectedFormat });
});

elements.urlInput.addEventListener('input', () => {
    if (elements.urlInput.value.trim()) {
        setHint('Press download to queue the job.');
    }
});

connectWebSocket();
