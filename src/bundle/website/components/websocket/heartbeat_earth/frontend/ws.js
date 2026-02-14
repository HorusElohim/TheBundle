import { HeartbeatMonitorComponent } from "../../common/frontend/heartbeat_monitor.js";
const HEARTBEAT_EARTH_CONFIG = {
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
};
class HeartbeatEarthComponent extends HeartbeatMonitorComponent {
    constructor(element) {
        super(element, HEARTBEAT_EARTH_CONFIG);
    }
}
document.querySelectorAll(HEARTBEAT_EARTH_CONFIG.selector).forEach((element) => {
    new HeartbeatEarthComponent(element);
});
//# sourceMappingURL=ws.js.map