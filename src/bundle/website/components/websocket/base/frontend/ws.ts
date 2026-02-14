type WebSocketPayload = string | object;

type ChannelEventMap = {
    connecting: { url: string };
    open: void;
    close: { event: CloseEvent };
    error: { event: Event };
    message: { raw: unknown; data: unknown; event: MessageEvent };
};

export type WebSocketChannelOptions = {
    reconnectDelayMs?: number;
    protocols?: string | string[];
};

export type AttachChannelOptions = WebSocketChannelOptions & {
    path?: string;
};

type EventHandler<K extends keyof ChannelEventMap> = (event: CustomEvent<ChannelEventMap[K]>) => void;

const buildWsUrl = (path: string): string => {
    if (path.startsWith("ws://") || path.startsWith("wss://")) {
        return path;
    }
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    return `${protocol}://${window.location.host}${path}`;
};

const parsePayload = (payload: unknown): unknown => {
    if (typeof payload !== "string") {
        return payload;
    }
    try {
        return JSON.parse(payload);
    } catch {
        return payload;
    }
};

export class WebSocketChannel {
    readonly url: string;
    private readonly options: WebSocketChannelOptions;
    private readonly target: EventTarget;
    private socket: WebSocket | null;
    private reconnectTimer: number | null;
    private closed: boolean;

    constructor(url: string, options: WebSocketChannelOptions = {}) {
        this.url = url;
        this.options = options;
        this.target = new EventTarget();
        this.socket = null;
        this.reconnectTimer = null;
        this.closed = false;
    }

    on<K extends keyof ChannelEventMap>(type: K, handler: EventHandler<K>): () => void {
        const wrapped = handler as EventListener;
        this.target.addEventListener(type, wrapped);
        return () => this.target.removeEventListener(type, wrapped);
    }

    connect(): void {
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

    close(): void {
        this.closed = true;
        if (this.reconnectTimer !== null) {
            window.clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        this.socket?.close();
    }

    send(payload: WebSocketPayload): boolean {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            return false;
        }
        const value = typeof payload === "string" ? payload : JSON.stringify(payload);
        this.socket.send(value);
        return true;
    }

    isOpen(): boolean {
        return this.socket?.readyState === WebSocket.OPEN;
    }

    private scheduleReconnect(): void {
        if (this.closed || this.reconnectTimer !== null) {
            return;
        }
        const delay = this.options.reconnectDelayMs ?? 1500;
        this.reconnectTimer = window.setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, delay);
    }

    private emit<K extends keyof ChannelEventMap>(type: K, detail: ChannelEventMap[K]): void {
        this.target.dispatchEvent(new CustomEvent(type, { detail }));
    }
}

export class PeriodicTask {
    private readonly tick: () => boolean;
    private timer: number | null;
    private pendingRuns: number;

    constructor(tick: () => boolean) {
        this.tick = tick;
        this.timer = null;
        this.pendingRuns = 0;
    }

    start(count: number, cadenceMs: number): void {
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

    stop(): void {
        if (this.timer !== null) {
            window.clearInterval(this.timer);
            this.timer = null;
        }
        this.pendingRuns = 0;
    }

    isRunning(): boolean {
        return this.timer !== null;
    }

    remaining(): number {
        return this.pendingRuns;
    }
}

const channels = new Map<string, WebSocketChannel>();

export const createPeriodicSender = (send: () => boolean) => new PeriodicTask(send);

export const getWebSocketChannel = (path: string, options: WebSocketChannelOptions = {}): WebSocketChannel => {
    const url = buildWsUrl(path);
    if (!channels.has(url)) {
        channels.set(url, new WebSocketChannel(url, options));
    }
    return channels.get(url)!;
};

export const attachWebSocketComponent = (element: HTMLElement | null, options: AttachChannelOptions = {}): WebSocketChannel | null => {
    const path = element?.dataset?.wsPath || options.path;
    if (!path) {
        return null;
    }
    const channel = getWebSocketChannel(path, options);
    channel.connect();
    return channel;
};

export class WebSocketComponent {
    protected readonly element: HTMLElement;
    protected readonly options: AttachChannelOptions;
    protected channel: WebSocketChannel | null;

    constructor(element: HTMLElement, options: AttachChannelOptions = {}) {
        this.element = element;
        this.options = options;
        this.channel = null;
    }

    connect(): WebSocketChannel | null {
        if (!this.channel) {
            this.channel = attachWebSocketComponent(this.element, this.options);
        }
        return this.channel;
    }

    on<K extends keyof ChannelEventMap>(type: K, handler: EventHandler<K>): (() => void) | undefined {
        return this.channel?.on(type, handler);
    }

    send(payload: WebSocketPayload): boolean {
        return this.channel?.send(payload) ?? false;
    }

    isOpen(): boolean {
        return this.channel?.isOpen() ?? false;
    }
}
