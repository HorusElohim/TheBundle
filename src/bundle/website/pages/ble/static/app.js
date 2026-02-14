import { wsNotifier } from '/static/js/ws-status.js';

const listEl = document.getElementById('device-list');
const deviceCountEl = document.getElementById('device-count');
const avgRssiEl = document.getElementById('avg-rssi');
const searchInput = document.getElementById('search');
const intervalInput = document.getElementById('refresh-interval');
const intervalValueEl = document.getElementById('interval-value');
const statusEl = document.getElementById('connection-status');
const streamToggle = document.getElementById('stream-toggle');
const detailPanel = document.getElementById('device-detail');
const detailBody = document.getElementById('detail-body');
const detailClose = document.getElementById('detail-close');
const detailNameEl = document.getElementById('detail-name');
const detailAddressEl = document.getElementById('detail-address');

const state = {
    devices: [],
    selectedAddress: null,
};

let socket;
let reconnectTimer;
let allowReconnect = true;
let isPaused = false;
const notify = wsNotifier('BLE');

function setStatus(label, variant = 'neutral') {
    const base = 'status-pill';
    statusEl.className = variant === 'neutral' ? base : `${base} ${variant}`;
    statusEl.textContent = label;
}

function showMessage(message) {
    listEl.innerHTML = `<p class="muted">${message}</p>`;
    deviceCountEl.textContent = '0';
    avgRssiEl.textContent = '-- dBm';
}

function updateIntervalLabel() {
    intervalValueEl.textContent = `${intervalInput.value}s`;
}

function applyFilters() {
    const term = searchInput.value.trim().toLowerCase();

    return state.devices
        .filter((device) => {
            if (!term) return true;
            return (
                device.name.toLowerCase().includes(term) ||
                device.address.toLowerCase().includes(term)
            );
        })
        .sort((a, b) => {
            const aSignal = Number.isFinite(a.signal) ? a.signal : -200;
            const bSignal = Number.isFinite(b.signal) ? b.signal : -200;
            return bSignal - aSignal;
        });
}

function formatSignal(value) {
    return value == null || Number.isNaN(value) ? '--' : `${value} dBm`;
}

function formatTx(value) {
    return value == null || Number.isNaN(value) ? '--' : `${value} dBm`;
}

function renderList(devices) {
    if (!devices.length) {
        showMessage('No devices found during the last sweep.');
        return;
    }

    const rssiAvg = devices.reduce((acc, device) => acc + (device.signal ?? -200), 0) / devices.length;
    deviceCountEl.textContent = devices.length.toString();
    avgRssiEl.textContent = formatSignal(Math.round(rssiAvg));

    listEl.innerHTML = devices
        .map((device) => {
            const services = (device.services || []).slice(0, 3);
            const serviceMarkup = services.length
                ? `<div class="badge-group">${services
                      .map((svc) => `<span class="badge subtle">${svc}</span>`)
                      .join('')}</div>`
                : '';
            const txDisplay = device.tx_power == null ? '--' : `${device.tx_power} dBm`;
            return `
                <article class="device-card" data-address="${device.address}">
                    <div>
                        <p class="device-name">${device.name}</p>
                        <p class="device-meta">${device.address}</p>
                        <p class="device-meta">${device.manufacturer ?? 'Unknown manufacturer'}</p>
                        <p class="device-meta">Tx power ${txDisplay}</p>
                        ${serviceMarkup}
                    </div>
                    <div class="device-stats">
                        <div>
                            <p class="stat-label">Signal</p>
                            <p class="signal">${formatSignal(device.signal)}</p>
                        </div>
                        <div>
                            <p class="stat-label">Tx power</p>
                            <p class="tx">${formatTx(device.tx_power)}</p>
                        </div>
                    </div>
                </article>`;
        })
        .join('');
}

function renderDetail(device) {
    if (!device) {
        detailPanel.classList.add('hidden');
        detailPanel.classList.remove('visible');
        detailBody.innerHTML = '';
        detailNameEl.textContent = '--';
        detailAddressEl.textContent = '';
        return;
    }
    detailNameEl.textContent = device.name;
    detailAddressEl.textContent = device.address;
    const services = device.services?.length
        ? `<div class="badge-group">${device.services
              .map((svc) => `<span class="badge subtle">${svc}</span>`)
              .join('')}</div>`
        : '<p class="device-meta">No advertised services</p>';
    detailBody.innerHTML = `
        <div class="detail-row"><span>Manufacturer</span><strong>${device.manufacturer ?? 'Unknown'}</strong></div>
        <div class="detail-row"><span>Type</span><strong>${device.type}</strong></div>
        <div class="detail-row"><span>Signal</span><strong>${formatSignal(device.signal)}</strong></div>
        <div class="detail-row"><span>Tx power</span><strong>${formatTx(device.tx_power)}</strong></div>
        <div class="detail-row"><span>Services</span><div>${services}</div></div>
    `;
    detailPanel.classList.remove('hidden');
    detailPanel.classList.add('visible');
}

function openDetail(device) {
    state.selectedAddress = device.address;
    renderDetail(device);
}

function closeDetail() {
    state.selectedAddress = null;
    renderDetail(null);
}

function render() {
    const filtered = applyFilters();
    renderList(filtered);
}

function handleMessage(event) {
    try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'scan') {
            const scan = payload.data || {};
            state.devices = scan.devices || [];
            setStatus('Streaming', 'success');
            render();
            if (state.selectedAddress) {
                const selected = state.devices.find((device) => device.address === state.selectedAddress);
                if (selected) {
                    renderDetail(selected);
                } else {
                    closeDetail();
                }
            }
        } else if (payload.type === 'error') {
            setStatus('Error', 'error');
            showMessage(payload.message || 'Unable to load devices.');
        }
    } catch (error) {
        console.error('Malformed payload', error);
    }
}

function sendIntervalConfig() {
    if (socket?.readyState === WebSocket.OPEN) {
        socket.send(
            JSON.stringify({
                type: 'config',
                interval: Number(intervalInput.value),
            })
        );
    }
}

function scheduleReconnect() {
    clearTimeout(reconnectTimer);
    if (!allowReconnect) {
        return;
    }
    reconnectTimer = setTimeout(connectSocket, 3000);
}

function connectSocket() {
    clearTimeout(reconnectTimer);
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close(1000, 'reconnecting');
    }

    setStatus('Connecting...', 'neutral');
    notify.connecting();
    showMessage('Preparing live session...');

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${protocol}://${window.location.host}/ble/ws/scan`);
    socket.addEventListener('open', () => {
        setStatus('Streaming', 'success');
        notify.connected();
        sendIntervalConfig();
    });
    socket.addEventListener('message', handleMessage);
    socket.addEventListener('close', () => {
        socket = null;
        if (isPaused) {
            setStatus('Paused', 'neutral');
            notify.disconnected();
            return;
        }
        setStatus('Disconnected', 'error');
        notify.disconnected();
        showMessage('Disconnected from BLE session. Reconnecting...');
        scheduleReconnect();
    });
    socket.addEventListener('error', () => {
        notify.error();
        socket.close();
    });
}

function pauseStream() {
    if (isPaused) return;
    isPaused = true;
    allowReconnect = false;
    streamToggle.textContent = 'Resume stream';
    setStatus('Paused', 'neutral');
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close(1000, 'paused');
    }
}

function resumeStream() {
    if (!isPaused) return;
    isPaused = false;
    allowReconnect = true;
    streamToggle.textContent = 'Pause stream';
    showMessage('Connecting to scanner...');
    connectSocket();
}

function toggleStream() {
    if (isPaused) {
        resumeStream();
    } else {
        pauseStream();
    }
}

function handleCardClick(event) {
    const card = event.target.closest('.device-card');
    if (!card) return;
    const device = state.devices.find((item) => item.address === card.dataset.address);
    if (device) {
        openDetail(device);
    }
}

listEl.addEventListener('click', handleCardClick);
detailClose.addEventListener('click', closeDetail);
detailPanel.addEventListener('click', (event) => {
    if (event.target === detailPanel) {
        closeDetail();
    }
});
window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        closeDetail();
    }
});
searchInput.addEventListener('input', render);
intervalInput.addEventListener('input', updateIntervalLabel);
intervalInput.addEventListener('change', sendIntervalConfig);
streamToggle.addEventListener('click', toggleStream);

updateIntervalLabel();
showMessage('Connecting to scanner...');
connectSocket();
