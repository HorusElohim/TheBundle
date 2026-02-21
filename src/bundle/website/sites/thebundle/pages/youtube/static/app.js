const DEFAULT_HINT = '';
const EMPTY_THUMBNAIL = 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=';
import { wsNotifier } from '/static/js/ws-status.js';
const elements = {
    urlInput: document.getElementById('youtube-url'),
    probeButton: document.getElementById('probe-btn'),
    mp4Button: document.getElementById('mp4-btn'),
    mp3Button: document.getElementById('mp3-btn'),
    formatActions: document.getElementById('format-actions'),
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
};
const state = {
    ws: null,
    reconnectTimer: null,
    pendingPayload: null,
    totalBytes: 0,
    downloadedBytes: 0,
    currentTrack: null,
    currentAction: null,
    currentFormat: 'mp4',
    probedUrl: '',
    probeTimer: null,
    skipNextInputProbe: false,
    lastUpdateTime: 0,
    lastProgressBytes: 0,
    lastErrorMessage: '',
};
const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/youtube/download_track`;
const notify = wsNotifier('YouTube');
function normalizeThumbnailUrl(value) {
    const url = (value || '').trim();
    if (!url) {
        return EMPTY_THUMBNAIL;
    }
    if (url.startsWith('http://') ||
        url.startsWith('https://') ||
        url.startsWith('//') ||
        url.startsWith('/') ||
        url.startsWith('./') ||
        url.startsWith('../') ||
        url.startsWith('data:') ||
        url.startsWith('blob:')) {
        return url;
    }
    return EMPTY_THUMBNAIL;
}
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
    elements.probeButton.disabled = isBusy;
    elements.mp4Button.disabled = isBusy;
    elements.mp3Button.disabled = isBusy;
    elements.probeButton.textContent = isBusy ? 'Working...' : 'Resolve';
}
function showActionButtons() {
    elements.formatActions.classList.remove('hidden');
}
function hideActionButtons() {
    elements.formatActions.classList.add('hidden');
}
function clearProbeTimer() {
    if (!state.probeTimer) {
        return;
    }
    clearTimeout(state.probeTimer);
    state.probeTimer = null;
}
function looksLikeYoutubeUrl(value) {
    const normalized = String(value || '').trim().toLowerCase();
    return normalized.includes('youtube.com/') || normalized.includes('youtu.be/');
}
function showMetadata(track) {
    elements.metadataCard.classList.remove('hidden');
    elements.thumbnail.src = normalizeThumbnailUrl(track.thumbnail_url || '');
    elements.trackTitle.textContent = track.title || 'Unknown title';
    elements.trackAuthor.textContent = track.author || 'Unknown author';
    showActionButtons();
}
function hideMetadata() {
    elements.metadataCard.classList.add('hidden');
    elements.trackTitle.textContent = '--';
    elements.trackAuthor.textContent = '--';
    elements.thumbnail.src = EMPTY_THUMBNAIL;
    hideActionButtons();
}
function resetResolvedState() {
    state.currentTrack = null;
    state.probedUrl = '';
    hideMetadata();
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
        elements.progressBytes.textContent = 'Streaming...';
        return;
    }
    const percentage = Math.min(100, (bytes / total) * 100);
    elements.progressFill.style.width = `${percentage}%`;
    elements.progressPercentage.textContent = `${percentage.toFixed(1)}%`;
    const formatBytes = (value) => value > 1024 * 1024 ? `${(value / (1024 * 1024)).toFixed(1)} MB` : `${(value / 1024).toFixed(1)} KB`;
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
    const safeThumb = normalizeThumbnailUrl(track?.thumbnail_url);
    card.innerHTML = `
        <div class="history-thumb">
            <img src="${safeThumb}" alt="Thumbnail">
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
        if (state.currentAction) {
            setBusy(false);
            setStatusMessage('Connection lost. Reconnecting...');
            setHint('Connection dropped, please retry once reconnected.', 'error');
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
        if (state.currentAction) {
            setBusy(false);
            setStatusMessage('Connection error');
            setHint('Connection error, try again in a moment.', 'error');
        }
    });
}
function sendRequest(payload) {
    state.currentAction = payload.action || 'download';
    state.currentFormat = payload.format || 'mp4';
    state.lastErrorMessage = '';
    resetProgress();
    setBusy(true);
    if (state.currentAction === 'probe') {
        setHint('Resolving...');
    }
    else {
        setHint('Queuing job...');
    }
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify(payload));
    }
    else {
        state.pendingPayload = payload;
        connectWebSocket();
    }
}
function requestProbe(youtubeUrl) {
    const normalizedUrl = youtubeUrl.trim();
    clearProbeTimer();
    if (!normalizedUrl || !looksLikeYoutubeUrl(normalizedUrl)) {
        return;
    }
    if (state.currentAction === 'probe' && state.probedUrl === normalizedUrl) {
        return;
    }
    if (state.probedUrl === normalizedUrl && state.currentTrack) {
        return;
    }
    state.probedUrl = normalizedUrl;
    setStatusMessage('Resolving...');
    sendRequest({ youtube_url: normalizedUrl, format: 'mp4', action: 'probe' });
}
function scheduleProbe(youtubeUrl) {
    const normalizedUrl = youtubeUrl.trim();
    clearProbeTimer();
    if (!looksLikeYoutubeUrl(normalizedUrl)) {
        return;
    }
    state.probeTimer = setTimeout(() => {
        state.probeTimer = null;
        requestProbe(normalizedUrl);
    }, 400);
}
function requestDownload(format) {
    const youtubeUrl = elements.urlInput.value.trim();
    if (!youtubeUrl) {
        setHint('Paste a valid YouTube link first.', 'error');
        return;
    }
    if (state.currentAction === 'probe' && state.probedUrl === youtubeUrl) {
        setHint('Still resolving... please wait.');
        return;
    }
    const needsProbe = youtubeUrl !== state.probedUrl || !state.currentTrack;
    if (needsProbe) {
        setHint('Resolve the URL first.', 'error');
        requestProbe(youtubeUrl);
        return;
    }
    sendRequest({ youtube_url: youtubeUrl, format, action: 'download' });
}
function isFailureMessage(value) {
    const text = String(value || '').toLowerCase();
    return (text.includes('failed') ||
        text.includes('error') ||
        text.includes('unable') ||
        text.includes('unavailable') ||
        text.includes('status: 403') ||
        text.includes('forbidden'));
}
function handleMessage(message) {
    switch (message.type) {
        case 'metadata':
            state.currentTrack = message;
            showMetadata(message);
            setStatusMessage('Track resolved');
            setHint('Choose MP4 or MP3.');
            break;
        case 'downloader_start':
            state.totalBytes = message.total || 0;
            state.downloadedBytes = 0;
            updateProgress(0, state.totalBytes);
            elements.phaseLabel.textContent = 'Downloading';
            setStatusMessage('Starting transfer...');
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
            if (isFailureMessage(message.info_message)) {
                state.lastErrorMessage = message.info_message || 'Download failed.';
                setHint(state.lastErrorMessage, 'error');
            }
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
            setBusy(false);
            if (state.currentAction === 'probe') {
                if (state.lastErrorMessage) {
                    setStatusMessage('Probe failed');
                    setHint(state.lastErrorMessage, 'error');
                }
                else {
                    setStatusMessage('Ready');
                    setHint('Choose MP4 or MP3.');
                }
            }
            else if (state.lastErrorMessage) {
                setStatusMessage('Transfer failed');
                setHint(state.lastErrorMessage, 'error');
                elements.phaseLabel.textContent = 'Failed';
            }
            else {
                setStatusMessage('Download ready');
                setHint('You can download again with MP4 or MP3.');
            }
            state.currentAction = null;
            state.lastErrorMessage = '';
            break;
        default:
            console.debug('Unhandled message', message);
    }
}
elements.probeButton?.addEventListener('click', () => {
    const youtubeUrl = elements.urlInput.value.trim();
    if (!youtubeUrl) {
        setHint('Paste a valid YouTube link first.', 'error');
        return;
    }
    requestProbe(youtubeUrl);
});
elements.mp4Button?.addEventListener('click', () => requestDownload('mp4'));
elements.mp3Button?.addEventListener('click', () => requestDownload('mp3'));
elements.urlInput.addEventListener('input', () => {
    if (state.skipNextInputProbe) {
        state.skipNextInputProbe = false;
        return;
    }
    const youtubeUrl = elements.urlInput.value.trim();
    resetResolvedState();
    if (youtubeUrl) {
        scheduleProbe(youtubeUrl);
    }
    else {
        setHint(DEFAULT_HINT);
    }
});
elements.urlInput.addEventListener('paste', () => {
    state.skipNextInputProbe = true;
    clearProbeTimer();
    setTimeout(() => {
        const youtubeUrl = elements.urlInput.value.trim();
        resetResolvedState();
        if (youtubeUrl) {
            requestProbe(youtubeUrl);
        }
    }, 0);
});
elements.thumbnail.onerror = () => {
    elements.thumbnail.src = EMPTY_THUMBNAIL;
};
hideActionButtons();
connectWebSocket();
//# sourceMappingURL=app.js.map