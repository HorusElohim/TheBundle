const buildWsUrl = (path) => {
    if (path.startsWith("ws://") || path.startsWith("wss://")) {
        return path;
    }
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    return `${protocol}://${window.location.host}${path}`;
};
const parsePayload = (payload) => {
    if (typeof payload !== "string") {
        return payload;
    }
    try {
        return JSON.parse(payload);
    }
    catch {
        return payload;
    }
};
export class WebSocketChannel {
    url;
    options;
    target;
    socket;
    reconnectTimer;
    closed;
    constructor(url, options = {}) {
        this.url = url;
        this.options = options;
        this.target = new EventTarget();
        this.socket = null;
        this.reconnectTimer = null;
        this.closed = false;
    }
    on(type, handler) {
        const wrapped = handler;
        this.target.addEventListener(type, wrapped);
        return () => this.target.removeEventListener(type, wrapped);
    }
    connect() {
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
            return;
        }
        this.closed = false;
        this.emit("connecting", { url: this.url });
        this.socket = new WebSocket(this.url, this.options.protocols);
        this.socket.addEventListener("open", () => this.emit("open", undefined));
        this.socket.addEventListener("message", (event) => {
            this.emit("message", { raw: event.data, data: parsePayload(event.data), event });
        });
        this.socket.addEventListener("close", (event) => {
            this.emit("close", { event });
            this.scheduleReconnect();
        });
        this.socket.addEventListener("error", (event) => this.emit("error", { event }));
    }
    close() {
        this.closed = true;
        if (this.reconnectTimer !== null) {
            window.clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        this.socket?.close();
    }
    send(payload) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            return false;
        }
        const value = typeof payload === "string" ? payload : JSON.stringify(payload);
        this.socket.send(value);
        return true;
    }
    isOpen() {
        return this.socket?.readyState === WebSocket.OPEN;
    }
    scheduleReconnect() {
        if (this.closed || this.reconnectTimer !== null) {
            return;
        }
        const delay = this.options.reconnectDelayMs ?? 1500;
        this.reconnectTimer = window.setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, delay);
    }
    emit(type, detail) {
        this.target.dispatchEvent(new CustomEvent(type, { detail }));
    }
}
export class PeriodicTask {
    tick;
    timer;
    pendingRuns;
    constructor(tick) {
        this.tick = tick;
        this.timer = null;
        this.pendingRuns = 0;
    }
    start(count, cadenceMs) {
        this.stop();
        this.pendingRuns = Number.isFinite(count) ? count : Number.POSITIVE_INFINITY;
        const run = () => {
            if (this.pendingRuns === 0) {
                this.stop();
                return;
            }
            if (this.tick()) {
                if (this.pendingRuns !== Number.POSITIVE_INFINITY) {
                    this.pendingRuns = Math.max(0, this.pendingRuns - 1);
                }
                if (this.pendingRuns === 0) {
                    this.stop();
                }
            }
        };
        run();
        if (this.pendingRuns !== 0 && (this.pendingRuns === Number.POSITIVE_INFINITY || this.pendingRuns > 1)) {
            this.timer = window.setInterval(run, cadenceMs);
        }
    }
    stop() {
        if (this.timer !== null) {
            window.clearInterval(this.timer);
            this.timer = null;
        }
        this.pendingRuns = 0;
    }
    isRunning() {
        return this.timer !== null;
    }
    remaining() {
        return this.pendingRuns;
    }
}
export const createPeriodicSender = (send) => new PeriodicTask(send);
export const getWebSocketChannel = (path, options = {}) => {
    const url = buildWsUrl(path);
    return new WebSocketChannel(url, options);
};
export const closeAllWebSocketChannels = () => {
    // Deprecated: channels are no longer shared globally.
};
export const attachWebSocketComponent = (element, options = {}) => {
    const path = element?.dataset?.wsPath || options.path;
    if (!path) {
        return null;
    }
    const channel = getWebSocketChannel(path, options);
    channel.connect();
    return channel;
};
export class WebSocketComponent {
    element;
    options;
    channel;
    constructor(element, options = {}) {
        this.element = element;
        this.options = options;
        this.channel = null;
    }
    connect() {
        if (!this.channel) {
            this.channel = attachWebSocketComponent(this.element, this.options);
        }
        return this.channel;
    }
    on(type, handler) {
        return this.channel?.on(type, handler);
    }
    send(payload) {
        return this.channel?.send(payload) ?? false;
    }
    isOpen() {
        return this.channel?.isOpen() ?? false;
    }
}
//# sourceMappingURL=ws.js.map