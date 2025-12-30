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

function formatMessage(label, progress, detail) {
    if (typeof progress === "number") {
        const pct = Math.round(Math.max(0, Math.min(1, progress)) * 100);
        return detail ? `${label}: ${pct}% · ${detail}` : `${label}: ${pct}%`;
    }
    return detail ? `${label}: ${detail}` : label;
}

export function createUsdLoader(label = "USD") {
    const container = ensureContainer();
    let toast = null;
    let closeTimer = null;

    const show = (message, variant = "neutral") => {
        if (!toast) {
            toast = document.createElement("div");
            container.appendChild(toast);
        }
        toast.className = `ws-toast ${variant}`;
        toast.textContent = message;
    };

    const clearTimer = () => {
        if (closeTimer) {
            window.clearTimeout(closeTimer);
            closeTimer = null;
        }
    };

    return {
        start(progress = 0, detail = "Loading…") {
            clearTimer();
            show(formatMessage(label, progress, detail), "neutral");
        },
        update(progress, detail) {
            clearTimer();
            show(formatMessage(label, progress, detail), "neutral");
        },
        success(detail = "Scene ready") {
            clearTimer();
            show(formatMessage(label, undefined, detail), "success");
            closeTimer = window.setTimeout(() => this.hide(), 1800);
        },
        error(detail = "Error") {
            clearTimer();
            show(formatMessage(label, undefined, detail), "error");
            closeTimer = window.setTimeout(() => this.hide(), 2400);
        },
        hide() {
            clearTimer();
            if (!toast) {
                return;
            }
            toast.classList.add("fade");
            const element = toast;
            toast = null;
            window.setTimeout(() => element.remove(), 220);
        },
    };
}
