declare module "/static/js/ws-status.js" {
    export function wsNotifier(label?: string): {
        connecting(): void;
        connected(): void;
        disconnected(): void;
        error(): void;
    };
}

declare module "/components-static/websocket/base/frontend/ws.js" {
    export function getWebSocketChannel(path: string): {
        on(type: string, handler: (...args: unknown[]) => void): () => void;
        connect(): void;
    };
}
