import { WebSocketWidget } from "../headless/ws.js";

class ToastWidget extends WebSocketWidget {
    constructor(element) {
        super(element, { reconnectDelayMs: 1500 });
        this.element = element;
        this.status = element.querySelector('[data-role="status"]');
        this.list = element.querySelector('[data-role="toast-list"]');
        this.maxItems = 6;
        this.bind();
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
        const item = document.createElement("div");
        item.className = "ws-toast__item";
        const title = document.createElement("div");
        title.className = "ws-toast__item-title";
        title.textContent = "Message";
        const body = document.createElement("div");
        body.className = "ws-toast__item-body";
        body.textContent = typeof payload === "string" ? payload : JSON.stringify(payload);
        item.appendChild(title);
        item.appendChild(body);
        this.list.prepend(item);
        const children = this.list.querySelectorAll(".ws-toast__item");
        if (children.length > this.maxItems) {
            children[children.length - 1].remove();
        }
    }

    bind() {
        this.connectChannel();
    }

    connectChannel() {
        this.channel = this.connect();
        if (!this.channel) {
            return;
        }

        this.on("connecting", () => this.setStatus("Connecting"));
        this.on("open", () => this.setStatus("Connected"));
        this.on("message", (event) => {
            this.pushToast(event.detail?.data ?? "message");
        });
        this.on("close", () => this.setStatus("Disconnected"));
        this.on("error", () => this.setStatus("Error"));
    }
}

document.querySelectorAll('[data-widget="ws-toast"]').forEach((element) => {
    new ToastWidget(element);
});
