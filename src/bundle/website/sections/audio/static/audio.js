import { wsNotifier } from "/static/js/ws-status.js";

const config = window.BUNDLE_AUDIO_CONFIG || {};
const wsEndpoint = config.wsEndpoint || "/ws/audio";

let socket;
let audioState = null;
let waveformChunk = [];
let isSelecting = false;
let selectionStartPx = 0;
let isPanning = false;
let panStartPx = 0;
let panStartOffset = 0;
let selectionPreview = null;
const pendingMessages = [];
const VIEW_THROTTLE_MS = 50;
let pendingView = null;
let viewTimer = null;
let lastViewSentAt = 0;
let autoFitNext = false;
let playbackRaf = null;

const canvas = document.getElementById("waveform");
const waveformStage = document.getElementById("waveform-stage");
const waveformEmpty = document.getElementById("waveform-empty");
const ctx = canvas.getContext("2d");
const pathInput = document.getElementById("audio-path");
const fileInput = document.getElementById("audio-upload");
const loadButton = document.getElementById("load-audio");
const uploadDrop = document.getElementById("upload-drop");
const statusText = document.getElementById("status-text");
const selectionText = document.getElementById("selection");
const clearTransforms = document.getElementById("clear-transforms");
const playToggle = document.getElementById("play-toggle");
const timeLabel = document.getElementById("playback-time");
const audioElement = document.getElementById("audio-player");
const dpr = window.devicePixelRatio || 1;
const notify = wsNotifier("Audio");

function protocolSend(type, payload) {
    const message = { v: 1, type, payload };
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        pendingMessages.push(message);
        return;
    }
    socket.send(JSON.stringify(message));
}

function flushPendingMessages() {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        return;
    }
    while (pendingMessages.length) {
        socket.send(JSON.stringify(pendingMessages.shift()));
    }
}

function sendPendingView() {
    if (!pendingView) {
        viewTimer = null;
        return;
    }
    lastViewSentAt = performance.now();
    protocolSend("audio.view.set", pendingView);
    pendingView = null;
    viewTimer = null;
}

function scheduleViewUpdate(zoom, offset_sec) {
    pendingView = { zoom, offset_sec };
    const now = performance.now();
    const elapsed = now - lastViewSentAt;
    if (elapsed >= VIEW_THROTTLE_MS) {
        sendPendingView();
        return;
    }
    if (!viewTimer) {
        viewTimer = setTimeout(sendPendingView, VIEW_THROTTLE_MS - elapsed);
    }
}

function connectSocket() {
    const url = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}${wsEndpoint}`;
    notify.connecting();
    socket = new WebSocket(url);
    socket.onopen = () => {
        statusText.textContent = "Connected";
        notify.connected();
        flushPendingMessages();
    };
    socket.onclose = () => {
        statusText.textContent = "Disconnected";
        notify.disconnected();
    };
    socket.onerror = () => {
        statusText.textContent = "Error";
        notify.error();
    };
    socket.onmessage = (event) => handleMessage(JSON.parse(event.data));
}

function handleMessage(message) {
    if (message.type === "audio.state") {
        audioState = message.payload;
        selectionPreview = null;
        if (statusText.textContent === "Loading…") {
            statusText.textContent = "Streaming…";
        }
        if (autoFitNext) {
            autoFitNext = false;
            fitViewToTrack();
        }
        updateSelectionLabel();
    } else if (message.type === "audio.waveform.chunk") {
        waveformChunk = message.payload.samples || [];
        statusText.textContent = "Ready";
        renderWaveform();
    } else if (message.type === "audio.error") {
        statusText.textContent = message.payload.message || "Error";
    }
}

function loadAudio() {
    const path = pathInput.value.trim();
    if (!path) {
        statusText.textContent = "Enter a path";
        return;
    }
    waveformChunk = [];
    renderWaveform();
    autoFitNext = true;
    protocolSend("audio.load", { path });
    statusText.textContent = "Loading…";
}

async function uploadAudio() {
    const file = fileInput.files[0];
    if (!file) {
        statusText.textContent = "Choose a file";
        return;
    }
    waveformChunk = [];
    renderWaveform();
    autoFitNext = true;
    const formData = new FormData();
    formData.append("file", file);
    statusText.textContent = "Uploading…";

    try {
        const response = await fetch("/api/audio/upload", {
            method: "POST",
            body: formData
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || "Upload failed");
        }
        if (payload.path) {
            pathInput.value = payload.path;
        }
        if (payload.url) {
            audioElement.src = payload.url;
            audioElement.load();
        }
        protocolSend("audio.load", { path: payload.path });
        statusText.textContent = "Loading…";
    } catch (error) {
        statusText.textContent = error.message || "Upload failed";
    }
}

function setCanvasSize() {
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.floor(rect.width * dpr));
    const height = Math.max(1, Math.floor(rect.height * dpr));
    const resized = canvas.width !== width || canvas.height !== height;
    if (resized) {
        canvas.width = width;
        canvas.height = height;
    }
    return resized;
}

function getViewPixelCount() {
    if (waveformChunk.length) {
        return waveformChunk.length;
    }
    return Math.max(1, canvas.clientWidth);
}

function fitViewToTrack() {
    if (!audioState) return;
    const sampleRate = audioState.source?.sample_rate || 1;
    const duration = audioState.source?.duration_sec || 0;
    const viewPixels = Math.max(1, canvas.clientWidth);
    const totalSamples = duration * sampleRate;
    const zoom = Math.min(10000, Math.max(1, totalSamples / viewPixels));
    scheduleViewUpdate(zoom, 0);
}

function ensurePlayheadVisible() {
    if (!audioState) return;
    const zoom = audioState.view?.zoom || 1;
    const sampleRate = audioState.source?.sample_rate || 1;
    const duration = audioState.source?.duration_sec || 0;
    const viewPixels = getViewPixelCount();
    const viewDuration = (viewPixels * zoom) / sampleRate;
    const offsetSec = audioState.view?.offset_sec || 0;
    const current = audioElement.currentTime || 0;
    const padding = viewDuration * 0.1;
    if (current < offsetSec + padding || current > offsetSec + viewDuration - padding) {
        const maxOffset = Math.max(0, duration - viewDuration);
        const newOffset = Math.min(maxOffset, Math.max(0, current - viewDuration * 0.5));
        scheduleViewUpdate(zoom, newOffset);
    }
}

function renderWaveform() {
    if (setCanvasSize()) {
        if (!waveformChunk.length) {
            waveformStage.classList.remove("has-waveform");
            return;
        }
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!waveformChunk.length) {
        waveformStage.classList.remove("has-waveform");
        return;
    }
    waveformStage.classList.add("has-waveform");
    const width = canvas.width;
    const height = canvas.height;
    if (width < 2 || height < 2) {
        return;
    }
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, width, height);
    ctx.clip();
    const midY = height / 2;
    const maxVal = Math.max(...waveformChunk.map((n) => Math.abs(n))) || 1;
    const bucketSize = waveformChunk.length / width;
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, "#5ad1ff");
    gradient.addColorStop(1, "#1f9cff");

    ctx.strokeStyle = gradient;
    ctx.lineWidth = Math.max(0.6, dpr * 0.7);
    ctx.lineCap = "round";
    ctx.beginPath();
    for (let x = 0; x < width; x += 1) {
        const start = Math.floor(x * bucketSize);
        const end = Math.min(waveformChunk.length, Math.floor((x + 1) * bucketSize));
        let peak = 0;
        if (end <= start) {
            peak = Math.abs(waveformChunk[start] || 0);
        } else {
            for (let i = start; i < end; i += 1) {
                const val = Math.abs(waveformChunk[i]);
                if (val > peak) peak = val;
            }
        }
        const normalized = Math.min(1, (peak / maxVal) * 1.6);
        const y1 = midY - normalized * (midY - 6);
        const y2 = midY + normalized * (midY - 6);
        ctx.moveTo(x + 0.5, y1);
        ctx.lineTo(x + 0.5, y2);
    }
    ctx.save();
    ctx.strokeStyle = "rgba(90, 209, 255, 0.22)";
    ctx.lineWidth = Math.max(1, dpr);
    ctx.shadowColor = "rgba(90, 209, 255, 0.35)";
    ctx.shadowBlur = 6 * dpr;
    ctx.stroke();
    ctx.restore();
    ctx.stroke();

    ctx.globalAlpha = 0.15;
    ctx.fillStyle = "#5ad1ff";
    ctx.fillRect(0, midY - 1, width, 2);
    ctx.globalAlpha = 1;

    const selection = selectionPreview || audioState?.view?.selection;
    if (selection && selection.length === 2) {
        const startX = positionFromTime(selection[0]);
        const endX = positionFromTime(selection[1]);
        const left = Math.max(0, Math.min(startX, endX));
        const right = Math.min(width, Math.max(startX, endX));
        if (right > 0 && left < width && right > left) {
            ctx.fillStyle = "rgba(90, 209, 255, 0.15)";
            ctx.fillRect(left, 0, right - left, height);
            ctx.strokeStyle = "rgba(90, 209, 255, 0.5)";
            ctx.lineWidth = Math.max(1, dpr);
            ctx.beginPath();
            ctx.moveTo(left + 0.5, 0);
            ctx.lineTo(left + 0.5, height);
            ctx.moveTo(right + 0.5, 0);
            ctx.lineTo(right + 0.5, height);
            ctx.stroke();
        }
    }

    if (audioState && audioElement.duration) {
        const zoom = audioState.view?.zoom || 1;
        const offsetSec = audioState.view?.offset_sec || 0;
        const sampleRate = audioState.source?.sample_rate || 1;
        const viewDuration = (getViewPixelCount() * zoom) / sampleRate;
        const playhead = (audioElement.currentTime - offsetSec) / viewDuration;
        if (playhead >= 0 && playhead <= 1) {
            ctx.beginPath();
            ctx.moveTo(playhead * canvas.width, 0);
            ctx.lineTo(playhead * canvas.width, canvas.height);
            ctx.strokeStyle = "rgba(255, 255, 255, 0.7)";
            ctx.lineWidth = Math.max(1, dpr);
            ctx.stroke();
        }
    }
    ctx.restore();
}

function sendView(zoomDelta, anchorPx = null) {
    if (!audioState) return;
    const currentZoom = audioState.view?.zoom || 1;
    const zoom = Math.min(10000, Math.max(1, currentZoom * zoomDelta));
    const sampleRate = audioState.source?.sample_rate || 1;
    const duration = audioState.source?.duration_sec || 0;
    const viewPixels = getViewPixelCount();
    const viewDuration = (viewPixels * zoom) / sampleRate;
    const maxOffset = Math.max(0, duration - viewDuration);

    let offset_sec = audioState.view?.offset_sec || 0;
    if (anchorPx != null) {
        const anchorTime = timeFromPosition(anchorPx);
        const anchorRatio = anchorPx / Math.max(1, canvas.clientWidth);
        offset_sec = anchorTime - anchorRatio * viewDuration;
    }
    offset_sec = Math.min(maxOffset, Math.max(0, offset_sec));
    scheduleViewUpdate(zoom, offset_sec);
}

function timeFromPosition(px) {
    if (!audioState) return 0;
    const samplesPerPixel = audioState.view?.zoom || 1;
    const sampleRate = audioState.source?.sample_rate || 1;
    const offsetSec = audioState.view?.offset_sec || 0;
    const viewPixels = getViewPixelCount();
    const ratio = px / Math.max(1, canvas.clientWidth);
    const sampleIndex = ratio * viewPixels;
    return offsetSec + (sampleIndex * samplesPerPixel) / sampleRate;
}

function positionFromTime(seconds) {
    if (!audioState) return 0;
    const samplesPerPixel = audioState.view?.zoom || 1;
    const sampleRate = audioState.source?.sample_rate || 1;
    const offsetSec = audioState.view?.offset_sec || 0;
    const viewPixels = getViewPixelCount();
    const sampleIndex = ((seconds - offsetSec) * sampleRate) / samplesPerPixel;
    const ratio = sampleIndex / Math.max(1, viewPixels);
    return ratio * canvas.width;
}

function clampTime(seconds) {
    const total = audioState?.source?.duration_sec || 0;
    return Math.min(Math.max(0, seconds), total);
}

function updateSelectionLabel() {
    if (!audioState || !audioState.view || !audioState.view.selection) {
        selectionText.textContent = "No selection";
        return;
    }
    const [start, end] = audioState.view.selection;
    selectionText.textContent = `Selection: ${start.toFixed(3)}s → ${end.toFixed(3)}s`;
}

function formatTime(seconds) {
    if (!Number.isFinite(seconds)) return "0:00";
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.floor(seconds % 60);
    return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

function updatePlaybackTime() {
    const current = audioElement.currentTime || 0;
    const total = audioElement.duration || 0;
    timeLabel.textContent = `${formatTime(current)} / ${formatTime(total)}`;
}

function playbackLoop() {
    updatePlaybackTime();
    if (!audioElement.paused) {
        ensurePlayheadVisible();
        renderWaveform();
        playbackRaf = requestAnimationFrame(playbackLoop);
    } else {
        playbackRaf = null;
    }
}

function startPlaybackLoop() {
    if (playbackRaf == null) {
        playbackRaf = requestAnimationFrame(playbackLoop);
    }
}

function stopPlaybackLoop() {
    if (playbackRaf != null) {
        cancelAnimationFrame(playbackRaf);
        playbackRaf = null;
    }
}

canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const delta = event.deltaY < 0 ? 0.9 : 1.1;
    sendView(delta, event.offsetX);
});

canvas.addEventListener("mousedown", (event) => {
    if (event.shiftKey) {
        isPanning = true;
        panStartPx = event.offsetX;
        panStartOffset = audioState?.view?.offset_sec || 0;
        return;
    }
    isSelecting = true;
    selectionStartPx = event.offsetX;
    selectionPreview = null;
});

canvas.addEventListener("mousemove", (event) => {
    const currentPx = event.offsetX;
    if (isPanning) {
        if (!audioState) return;
        const deltaPx = currentPx - panStartPx;
        const samplesPerPixel = audioState.view?.zoom || 1;
        const sampleRate = audioState.source?.sample_rate || 1;
        const duration = audioState.source?.duration_sec || 0;
        const viewPixels = getViewPixelCount();
        const viewDuration = (viewPixels * samplesPerPixel) / sampleRate;
        const maxOffset = Math.max(0, duration - viewDuration);
        const offset_sec = Math.min(maxOffset, Math.max(0, panStartOffset - (deltaPx * samplesPerPixel) / sampleRate));
        scheduleViewUpdate(samplesPerPixel, offset_sec);
        return;
    }
    if (!isSelecting) return;
    const start = timeFromPosition(selectionStartPx);
    const end = timeFromPosition(currentPx);
    selectionPreview = [Math.min(start, end), Math.max(start, end)];
    selectionText.textContent = `Selection: ${Math.min(start, end).toFixed(3)}s → ${Math.max(start, end).toFixed(3)}s`;
    renderWaveform();
});

canvas.addEventListener("mouseup", (event) => {
    if (isPanning) {
        isPanning = false;
        return;
    }
    if (!isSelecting) return;
    isSelecting = false;
    const endPx = event.offsetX;
    const start = timeFromPosition(selectionStartPx);
    const end = timeFromPosition(endPx);
    const deltaPx = Math.abs(endPx - selectionStartPx);
    if (deltaPx < 3) {
        const seekTime = clampTime(timeFromPosition(endPx));
        audioElement.currentTime = seekTime;
        updatePlaybackTime();
        renderWaveform();
    } else {
        protocolSend("audio.select", { start, end });
    }
    selectionPreview = null;
});

canvas.addEventListener("dblclick", (event) => {
    event.preventDefault();
    fitViewToTrack();
});

canvas.addEventListener("mouseleave", () => {
    isSelecting = false;
    isPanning = false;
    selectionPreview = null;
    renderWaveform();
});

loadButton.addEventListener("click", loadAudio);
clearTransforms.addEventListener("click", () => protocolSend("audio.transform.clear", {}));

uploadDrop.addEventListener("dragover", (event) => {
    event.preventDefault();
    uploadDrop.classList.add("is-dragging");
});
uploadDrop.addEventListener("dragleave", () => uploadDrop.classList.remove("is-dragging"));
uploadDrop.addEventListener("drop", (event) => {
    event.preventDefault();
    uploadDrop.classList.remove("is-dragging");
    if (event.dataTransfer?.files?.length) {
        fileInput.files = event.dataTransfer.files;
        uploadAudio();
    }
});
fileInput.addEventListener("change", (event) => {
    const target = event.currentTarget;
    if (!target || !target.files || !target.files.length) {
        return;
    }
    uploadAudio();
    target.value = "";
});

playToggle.addEventListener("click", () => {
    togglePlayback();
});

function togglePlayback() {
    if (!audioElement.src) {
        statusText.textContent = "Upload audio to play";
        return;
    }
    if (audioElement.paused) {
        audioElement.play();
        playToggle.textContent = "Pause";
    } else {
        audioElement.pause();
        playToggle.textContent = "Play";
    }
}

document.addEventListener("keydown", (event) => {
    if (event.code !== "Space") return;
    const target = event.target;
    const isEditable =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target?.isContentEditable;
    if (isEditable) return;
    event.preventDefault();
    togglePlayback();
});

audioElement.addEventListener("loadedmetadata", () => {
    updatePlaybackTime();
});

audioElement.addEventListener("timeupdate", () => {
    updatePlaybackTime();
    renderWaveform();
});

audioElement.addEventListener("play", () => {
    startPlaybackLoop();
});

audioElement.addEventListener("pause", () => {
    stopPlaybackLoop();
});

audioElement.addEventListener("ended", () => {
    playToggle.textContent = "Play";
    stopPlaybackLoop();
});
window.addEventListener("resize", () => {
    if (setCanvasSize()) {
        renderWaveform();
    }
});
setCanvasSize();
connectSocket();
