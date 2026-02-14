import { WebSocketComponent } from "../../base/frontend/ws.js";

type ToastBridgeEvent = {
    source?: string;
    body?: string;
};

class ToastComponent extends WebSocketComponent {
    private readonly status: HTMLElement | null;
    private readonly list: HTMLElement | null;
    private readonly maxItems: number;

    constructor(element: HTMLElement) {
        super(element, { reconnectDelayMs: 1500 });
        this.status = element.querySelector('[data-role="status"]');
        this.list = element.querySelector('[data-role="toast-list"]');
        this.maxItems = 6;
        this.bind();
    }

    private bind(): void {
        this.bindWebSocket();
        this.bindHeartbeatBridge();
    }

    private bindWebSocket(): void {
        this.channel = this.connect();
        if (!this.channel) {
            return;
        }
        this.on("connecting", () => this.setStatus("Connecting"));
        this.on("open", () => this.setStatus("Connected"));
        this.on("message", (event) => this.pushToast(event.detail?.data ?? "message"));
        this.on("close", () => this.setStatus("Disconnected"));
        this.on("error", () => this.setStatus("Error"));
    }

    private bindHeartbeatBridge(): void {
        window.addEventListener("bundle:toast", (event: Event) => {
            const payload = (event as CustomEvent<ToastBridgeEvent>).detail;
            if (!payload || payload.source !== "heartbeat-earth") {
                return;
            }
            this.pushToast(payload.body || "Heartbeat event");
        });
    }

    private setStatus(label: string): void {
        if (this.status) {
            this.status.textContent = label;
        }
    }

    private pushToast(payload: unknown): void {
        if (!this.list) {
            return;
        }
        const item = this.createToastItem(payload);
        this.list.prepend(item);
        this.trimOverflow();
    }

    private createToastItem(payload: unknown): HTMLElement {
        const item = document.createElement("div");
        item.className = "ws-toast__item";

        const title = document.createElement("div");
        title.className = "ws-toast__item-title";
        title.textContent = "Message";

        const body = document.createElement("div");
        body.className = "ws-toast__item-body";
        body.textContent = this.formatPayload(payload);

        item.append(title, body);
        return item;
    }

    private formatPayload(payload: unknown): string {
        return typeof payload === "string" ? payload : JSON.stringify(payload);
    }

    private trimOverflow(): void {
        if (!this.list) {
            return;
        }
        const children = this.list.querySelectorAll(".ws-toast__item");
        if (children.length > this.maxItems) {
            children[children.length - 1].remove();
        }
    }
}

document.querySelectorAll<HTMLElement>('[data-component="ws-toast"]').forEach((element) => {
    new ToastComponent(element);
});
