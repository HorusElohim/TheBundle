import { getWebSocketChannel } from "/components-static/websocket/base/component.js";

const status = document.querySelector('[data-role="ws-status"]');

if (status) {
    const typedStatus = status as HTMLElement;
    const path = typedStatus.dataset.wsPath || "/ws/ecc";
    const channel = getWebSocketChannel(path);

    const setStatus = (label: string) => {
        typedStatus.textContent = `WS: ${label}`;
    };

    channel.on("connecting", () => setStatus("connecting"));
    channel.on("open", () => setStatus("connected"));
    channel.on("close", () => setStatus("disconnected"));
    channel.on("error", () => setStatus("error"));

    channel.connect();
}

