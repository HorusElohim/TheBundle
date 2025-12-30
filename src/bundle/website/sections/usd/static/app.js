const pathInput = document.getElementById('usd-path');
const loadBtn = document.getElementById('load-btn');
const statusEl = document.getElementById('status');
const primCount = document.getElementById('prim-count');
const layerCount = document.getElementById('layer-count');
const metersPerUnit = document.getElementById('meters-per-unit');
const upAxis = document.getElementById('up-axis');
const errors = document.getElementById('errors');

const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const wsUrl = `${wsProtocol}://${window.location.host}/ws/usd`;
let socket;

function setStatus(message) {
    statusEl.textContent = message;
}

function showError(message) {
    errors.textContent = message;
    errors.classList.toggle('hidden', !message);
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
                break;
            case 'error':
                showError(payload.message || 'Unknown error');
                setStatus('Error loading scene');
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
    showError('');
}

loadBtn?.addEventListener('click', () => {
    const path = (pathInput?.value || '').trim();
    if (!path) {
        showError('Please enter a USD file path');
        return;
    }
    sendLoad(path);
});

pathInput?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        loadBtn?.click();
    }
});

setStatus('Waiting for load…');
