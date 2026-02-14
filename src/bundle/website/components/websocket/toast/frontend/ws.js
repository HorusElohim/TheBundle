import { WebSocketComponent } from "../../base/frontend/ws.js";
class ToastComponent extends WebSocketComponent {
    status;
    list;
    maxItems;
    constructor(element) {
        super(element, { reconnectDelayMs: 1500 });
        this.status = element.querySelector('[data-role="status"]');
        this.list = element.querySelector('[data-role="toast-list"]');
        this.maxItems = 24;
        this.bind();
    }
    bind() {
        this.setStatus("WS Feed Disabled");
    }
    setStatus(label) {
        if (this.status) {
            this.status.textContent = label;
        }
    }
    pushToast(payload) {
        if (!this.list) {
            return;
        }
        const item = this.createToastItem(payload);
        this.list.prepend(item);
        this.trimOverflow();
    }
    createToastItem(payload) {
        const item = document.createElement("div");
        item.className = "ws-toast__item";
        const title = document.createElement("div");
        title.className = "ws-toast__item-title";
        const feed = payload;
        const eventType = (feed?.event || "event").toUpperCase();
        const url = (feed?.url || "").replace(/^wss?:\/\/[^/]+/, "");
        title.textContent = `${eventType} ${url || ""}`.trim();
        const body = document.createElement("div");
        body.className = "ws-toast__item-body";
        body.textContent = this.formatPayload(feed?.payload ?? payload);
        item.append(title, body);
        return item;
    }
    formatPayload(payload) {
        return typeof payload === "string" ? payload : JSON.stringify(payload);
    }
    trimOverflow() {
        if (!this.list) {
            return;
        }
        const children = this.list.querySelectorAll(".ws-toast__item");
        if (children.length > this.maxItems) {
            children[children.length - 1].remove();
        }
    }
}
document.querySelectorAll('[data-component="ws-toast"]').forEach((element) => {
    new ToastComponent(element);
});
//# sourceMappingURL=ws.js.map