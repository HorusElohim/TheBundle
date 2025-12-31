import { createUsdLoader } from '/static/js/usd-loader.js';

const fileInput = document.getElementById('usd-file');
const uploadBtn = document.getElementById('upload-btn');
const dropTarget = document.getElementById('usd-drop-target');
const dropOverlay = document.getElementById('usd-drop-overlay');
const viewerFrame = document.getElementById('usd-viewer');
const statusEl = document.getElementById('status');
const primCount = document.getElementById('prim-count');
const layerCount = document.getElementById('layer-count');
const metersPerUnit = document.getElementById('meters-per-unit');
const upAxis = document.getElementById('up-axis');
const errors = document.getElementById('errors');

const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const wsUrl = `${wsProtocol}://${window.location.host}/ws/usd`;
let socket;
const loader = createUsdLoader('USD');
let loadingActive = false;
let loadingAutoClose;

function setStatus(message) {
    statusEl.textContent = message;
}

function showError(message) {
    errors.textContent = message;
    errors.classList.toggle('hidden', !message);
}

function startLoading(progress, detail) {
    loadingActive = true;
    loader.start(progress, detail);
}

function updateLoading(progress, detail) {
    if (!loadingActive) {
        return;
    }
    loader.update(progress, detail);
    if (progress >= 0.99) {
        finishLoading();
    }
}

function finishLoading(message) {
    if (!loadingActive) {
        return;
    }
    loadingActive = false;
    if (loadingAutoClose) {
        window.clearTimeout(loadingAutoClose);
        loadingAutoClose = undefined;
    }
    if (message) {
        loader.success(message);
    } else {
        loader.hide();
    }
}

async function uploadScene(file) {
    const formData = new FormData();
    formData.append('file', file);
    setStatus(`Uploading ${file.name}…`);
    showError('');
    const response = await fetch('/usd/upload', { method: 'POST', body: formData });
    if (!response.ok) {
        let detail = 'Upload failed';
        try {
            const payload = await response.json();
            detail = payload.detail || detail;
        } catch (err) {
            detail = await response.text();
        }
        throw new Error(detail);
    }
    return response.json();
}

function loadViewer(url) {
    if (!viewerFrame || !url) {
        return;
    }
    let resolvedUrl = url;
    try {
        resolvedUrl = new URL(url, window.location.origin).toString();
        const viewerUrl = new URL(viewerFrame.src, window.location.origin);
        viewerUrl.searchParams.set('file', resolvedUrl);
        viewerFrame.src = viewerUrl.toString();
    } catch (err) {
        console.warn('Unable to update viewer URL', err);
    }
    viewerFrame.contentWindow?.postMessage({ type: 'bundle:load', url: resolvedUrl }, window.location.origin);
}

function applySceneInfo(info) {
    primCount.textContent = info.prim_count ?? '--';
    layerCount.textContent = info.layer_count ?? '--';
    metersPerUnit.textContent = info.meters_per_unit ?? '--';
    upAxis.textContent = info.up_axis ?? '--';
}

function ensureSocket() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        return socket;
    }

    socket = new WebSocket(wsUrl);
    socket.addEventListener('open', () => setStatus('Connected. Ready for scene loads.'));
    socket.addEventListener('close', () => setStatus('Connection closed. Click load to reconnect.'));
    socket.addEventListener('error', () => showError('WebSocket connection error'));

    socket.addEventListener('message', (event) => {
        const payload = JSON.parse(event.data);
        switch (payload.type) {
            case 'scene_loaded':
                applySceneInfo(payload.info || {});
                setStatus('Scene loaded');
                showError('');
                updateLoading(0.85, 'Backend ready');
                if (loadingActive) {
                    if (loadingAutoClose) {
                        window.clearTimeout(loadingAutoClose);
                    }
                    loadingAutoClose = window.setTimeout(() => finishLoading('Scene ready'), 1500);
                }
                break;
            case 'error':
                showError(payload.message || 'Unknown error');
                setStatus('Error loading scene');
                loadingActive = false;
                loader.error(payload.message || 'Load failed');
                break;
            default:
                console.debug('Unhandled message', payload);
        }
    });

    return socket;
}

function sendLoad(path) {
    const ws = ensureSocket();
    if (ws.readyState === WebSocket.CONNECTING) {
        ws.addEventListener('open', () => sendLoad(path), { once: true });
        return;
    }
    ws.send(JSON.stringify({ type: 'load_scene', path }));
    setStatus('Loading scene…');
    if (!loadingActive) {
        startLoading(0.4, 'Initializing USD scene…');
    } else {
        updateLoading(0.4, 'Initializing USD scene…');
    }
    showError('');
}

async function handleFile(file) {
    if (!file) {
        showError('Please choose a USD file');
        return;
    }
    try {
        startLoading(0.1, 'Uploading file to server…');
        const payload = await uploadScene(file);
        if (!payload.path) {
            throw new Error('Upload did not return a scene path');
        }
        if (payload.url) {
            loadViewer(payload.url);
        }
        updateLoading(0.3, 'Sending scene to backend…');
        sendLoad(payload.path);
    } catch (err) {
        showError(err?.message || 'Unable to upload USD file');
        setStatus('Upload failed');
        loadingActive = false;
        loader.error('Upload failed');
    }
}

uploadBtn?.addEventListener('click', () => fileInput?.click());

fileInput?.addEventListener('change', () => {
    const [file] = fileInput.files || [];
    handleFile(file);
    fileInput.value = '';
});

let dragDepth = 0;
const hasFiles = (event) => Array.from(event.dataTransfer?.types || []).includes('Files');

const setDragActive = (active) => {
    dropTarget?.classList.toggle('drag-active', active);
};

document.addEventListener('dragenter', (event) => {
    if (!hasFiles(event)) {
        return;
    }
    dragDepth += 1;
    setDragActive(true);
});

document.addEventListener('dragleave', (event) => {
    if (!hasFiles(event)) {
        return;
    }
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) {
        setDragActive(false);
    }
});

document.addEventListener('dragover', (event) => {
    if (hasFiles(event)) {
        event.preventDefault();
    }
});

dropOverlay?.addEventListener('dragover', (event) => event.preventDefault());
dropOverlay?.addEventListener('drop', (event) => {
    event.preventDefault();
    dragDepth = 0;
    setDragActive(false);
    const [file] = event.dataTransfer?.files || [];
    handleFile(file);
});

dropOverlay?.addEventListener('click', () => fileInput?.click());
dropOverlay?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        fileInput?.click();
    }
});

window.addEventListener('message', (event) => {
    if (event.origin !== window.location.origin) {
        return;
    }
    const payload = event.data;
    if (!payload || payload.type !== 'bundle:viewer') {
        return;
    }
    if (payload.state === 'error') {
        showError(payload.detail || 'USD viewer failed to load');
        setStatus('Viewer error');
        loadingActive = false;
        loader.error(payload.detail || 'Viewer error');
        return;
    }
    if (typeof payload.progress === 'number') {
        updateLoading(payload.progress, payload.detail);
    }
    if (payload.state === 'loaded') {
        finishLoading('Scene ready');
    }
});

setStatus('Waiting for load…');
loader.hide();
