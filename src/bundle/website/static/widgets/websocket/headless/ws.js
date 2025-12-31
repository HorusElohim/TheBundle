const channels = new Map();

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
    } catch (error) {
        return payload;
    }
};

const createChannel = (url, options) => {
    const target = new EventTarget();
    let socket = null;
    let reconnectTimer = null;
    let closed = false;
    const reconnectDelayMs = options.reconnectDelayMs ?? 1500;

    const emit = (type, detail) => {
        target.dispatchEvent(new CustomEvent(type, { detail }));
    };

    const scheduleReconnect = () => {
        if (closed || reconnectTimer) {
            return;
        }
        reconnectTimer = window.setTimeout(() => {
            reconnectTimer = null;
            connect();
        }, reconnectDelayMs);
    };

    const connect = () => {
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
            return;
        }
        closed = false;
        emit("connecting", { url });
        socket = new WebSocket(url, options.protocols);

        socket.addEventListener("open", () => {
            emit("open");
        });

        socket.addEventListener("message", (event) => {
            emit("message", { raw: event.data, data: parsePayload(event.data), event });
        });

        socket.addEventListener("close", (event) => {
            emit("close", { event });
            scheduleReconnect();
        });

        socket.addEventListener("error", (event) => {
            emit("error", { event });
        });
    };

    const send = (payload) => {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            return false;
        }
        const value = typeof payload === "string" ? payload : JSON.stringify(payload);
        socket.send(value);
        return true;
    };

    const close = () => {
        closed = true;
        if (reconnectTimer) {
            window.clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
        if (socket) {
            socket.close();
        }
    };

    return {
        url,
        connect,
        close,
        send,
        on(type, handler) {
            target.addEventListener(type, handler);
            return () => target.removeEventListener(type, handler);
        },
        isOpen() {
            return socket?.readyState === WebSocket.OPEN;
        },
    };
};

export const createPeriodicSender = (send) => {
    let timer = null;
    let remaining = 0;

    const stop = () => {
        if (timer) {
            window.clearInterval(timer);
            timer = null;
        }
        remaining = 0;
    };

    const start = (count, cadenceMs) => {
        stop();
        remaining = Number.isFinite(count) ? count : Infinity;
        const tick = () => {
            if (remaining === 0) {
                stop();
                return;
            }
            if (send()) {
                if (remaining !== Infinity) {
                    remaining = Math.max(0, remaining - 1);
                }
                if (remaining === 0) {
                    stop();
                }
            }
        };

        tick();
        if (remaining !== 0 && (remaining === Infinity || remaining > 1)) {
            timer = window.setInterval(tick, cadenceMs);
        }
    };

    return {
        start,
        stop,
        isRunning() {
            return timer !== null;
        },
        remaining() {
            return remaining;
        },
    };
};

export const getWebSocketChannel = (path, options = {}) => {
    const url = buildWsUrl(path);
    if (!channels.has(url)) {
        channels.set(url, createChannel(url, options));
    }
    return channels.get(url);
};

export const attachWebSocketWidget = (element, options = {}) => {
    const path = element?.dataset?.wsPath || options.path;
    if (!path) {
        return null;
    }
    const channel = getWebSocketChannel(path, options);
    channel.connect();
    return channel;
};

export class WebSocketWidget {
    constructor(element, options = {}) {
        this.element = element;
        this.options = options;
        this.channel = null;
    }

    connect() {
        if (!this.channel) {
            this.channel = attachWebSocketWidget(this.element, this.options);
        }
        return this.channel;
    }

    on(type, handler) {
        return this.channel?.on(type, handler);
    }

    send(payload) {
        return this.channel?.send(payload);
    }

    isOpen() {
        return this.channel?.isOpen() ?? false;
    }
}
