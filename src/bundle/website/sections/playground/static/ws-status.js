import { getWebSocketChannel } from "/static/widgets/websocket/headless/ws.js";

const status = document.querySelector('[data-role="ws-status"]');

if (status) {
    const path = status.dataset.wsPath || "/ws/ecc";
    const channel = getWebSocketChannel(path);

    const setStatus = (label) => {
        status.textContent = `WS: ${label}`;
    };

    channel.on("connecting", () => setStatus("connecting"));
    channel.on("open", () => setStatus("connected"));
    channel.on("close", () => setStatus("disconnected"));
    channel.on("error", () => setStatus("error"));

    channel.connect();
}
