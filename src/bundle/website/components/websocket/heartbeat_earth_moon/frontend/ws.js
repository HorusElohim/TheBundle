import { attachHeartbeatOrbitMonitors } from "../../common/frontend/heartbeat_orbit.js";
attachHeartbeatOrbitMonitors({
    selector: '[data-component="ws-heartbeat-earth-moon"]',
    toastSource: "heartbeat-earth-moon",
    toastLabel: "Earth Moon",
    timeoutMessage: "Heartbeat timeout from Earth-Moon monitor.",
    colors: {
        tx: 0xef4444,
        rx: 0x4ade80,
    },
    labels: {
        tx: "Upload",
        rx: "Download",
    },
    planet: {
        style: "earth_moon",
        rotationY: 0,
    },
    nodes: {
        client: {
            lat: 34.0522,
            lon: -118.2437,
            color: 0xef4444,
            icon: "heart",
            label: "Client Heart",
        },
        server: {
            lat: 51.5074,
            lon: -0.1278,
            color: 0x4ade80,
            icon: "moon",
            label: "Server Moon",
        },
    },
});
//# sourceMappingURL=ws.js.map