const containerId = "ws-toast-container";

function ensureContainer() {
    let container = document.getElementById(containerId);
    if (!container) {
        container = document.createElement("div");
        container.id = containerId;
        container.className = "ws-toast-container";
        document.body.appendChild(container);
    }
    return container;
}

function showToast(message, variant = "neutral") {
    const container = ensureContainer();
    const toast = document.createElement("div");
    toast.className = `ws-toast ${variant}`;
    toast.textContent = message;
    container.appendChild(toast);
    // auto-remove
    setTimeout(() => {
        toast.classList.add("fade");
        setTimeout(() => toast.remove(), 220);
    }, 2000);
}

export function wsNotifier(label = "Connection") {
    return {
        connecting: () => showToast(`${label}: Connecting…`, "neutral"),
        connected: () => showToast(`${label}: Connected`, "success"),
        disconnected: () => showToast(`${label}: Disconnected`, "warning"),
        error: () => showToast(`${label}: Error`, "error"),
    };
}
