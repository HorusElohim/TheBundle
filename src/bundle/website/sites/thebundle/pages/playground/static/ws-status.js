const statusElement = document.querySelector('[data-role="ws-status"]');
const toWebSocketUrl = (path) => {
    if (path.startsWith("ws://") || path.startsWith("wss://")) {
        return path;
    }
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    return `${protocol}://${window.location.host}${path}`;
};
if (statusElement) {
    const typedStatus = statusElement;
    const path = typedStatus.dataset.wsPath || "/ws/ecc";
    const socket = new WebSocket(toWebSocketUrl(path));
    const setStatus = (label) => {
        typedStatus.textContent = `WS: ${label}`;
    };
    setStatus("connecting");
    socket.addEventListener("open", () => setStatus("connected"));
    socket.addEventListener("close", () => setStatus("disconnected"));
    socket.addEventListener("error", () => setStatus("error"));
}
//# sourceMappingURL=ws-status.js.map