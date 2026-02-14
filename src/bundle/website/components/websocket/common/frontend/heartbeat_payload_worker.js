const encoder = new TextEncoder();
let payloadCache = "";
let payloadCacheSize = 0;
const seed = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
function buildKeepaliveRaw(sentAt, payloadTargetBytes) {
    const base = { type: "keepalive", sent_at: sentAt, payload: "" };
    const baseRaw = JSON.stringify(base);
    const baseSize = encoder.encode(baseRaw).length;
    const contentBytes = Math.max(0, payloadTargetBytes - baseSize);
    if (contentBytes > payloadCacheSize) {
        let cache = payloadCache;
        while (cache.length < contentBytes) {
            const needed = contentBytes - cache.length;
            cache += needed >= seed.length ? seed : seed.slice(0, needed);
        }
        payloadCache = cache;
        payloadCacheSize = cache.length;
    }
    const payload = payloadCache.slice(0, contentBytes);
    return JSON.stringify({ type: "keepalive", sent_at: sentAt, payload });
}
self.addEventListener("message", (event) => {
    const detail = event.data;
    if (!detail || typeof detail.id !== "number") {
        return;
    }
    const raw = buildKeepaliveRaw(detail.sentAt, detail.payloadTargetBytes);
    self.postMessage({ id: detail.id, raw });
});
//# sourceMappingURL=heartbeat_payload_worker.js.map