const containerId = "ws-toast-container";

type RuntimeNotifier = {
    connecting(): void;
    connected(): void;
    disconnected(): void;
    error(): void;
};

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

function showToast(message: string, variant = "neutral") {
    const container = ensureContainer();
    const toast = document.createElement("div");
    toast.className = `ws-toast ${variant}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("fade");
        setTimeout(() => toast.remove(), 220);
    }, 2000);
}

export function wsNotifier(label = "Connection"): RuntimeNotifier {
    return {
        connecting: () => showToast(`${label}: Connecting...`, "neutral"),
        connected: () => showToast(`${label}: Connected`, "success"),
        disconnected: () => showToast(`${label}: Disconnected`, "warning"),
        error: () => showToast(`${label}: Error`, "error"),
    };
}

window.wsNotifier = wsNotifier;

