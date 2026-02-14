import { attachHeartbeatOrbitMonitors } from "../../common/frontend/heartbeat_orbit.js";
attachHeartbeatOrbitMonitors({
    selector: '[data-component="ws-heartbeat-earth"]',
    toastSource: "heartbeat-earth",
    toastLabel: "Earth",
    timeoutMessage: "Heartbeat timeout from Earth monitor.",
    colors: {
        tx: 0x4ade80,
        rx: 0xfb923c,
    },
    planet: {
        style: "earth",
        rotationY: 0,
    },
    nodes: {
        client: {
            lat: 37.7749,
            lon: -122.4194,
            color: 0x4ade80,
            icon: "dot",
            label: "Client",
        },
        server: {
            lat: 64.1466,
            lon: -21.9426,
            color: 0xfb923c,
            icon: "dot",
            label: "Server",
        },
    },
});
//# sourceMappingURL=ws.js.map