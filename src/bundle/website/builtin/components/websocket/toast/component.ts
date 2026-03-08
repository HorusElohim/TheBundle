import { WebSocketComponent } from "../base/component.js";

type WebSocketFeedEvent = {
    url?: string;
    event?: string;
    payload?: unknown;
    timestamp?: number;
};

class ToastComponent extends WebSocketComponent {
    private readonly status: HTMLElement | null;
    private readonly list: HTMLElement | null;
    private readonly maxItems: number;

    constructor(element: HTMLElement) {
        super(element, { reconnectDelayMs: 1500 });
        this.status = element.querySelector('[data-role="status"]');
        this.list = element.querySelector('[data-role="toast-list"]');
        this.maxItems = 24;
        this.bind();
    }

    private bind(): void {
        this.setStatus("WS Feed Disabled");
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
        const feed = payload as WebSocketFeedEvent;
        const eventType = (feed?.event || "event").toUpperCase();
        const url = (feed?.url || "").replace(/^wss?:\/\/[^/]+/, "");
        title.textContent = `${eventType} ${url || ""}`.trim();

        const body = document.createElement("div");
        body.className = "ws-toast__item-body";
        body.textContent = this.formatPayload(feed?.payload ?? payload);

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

