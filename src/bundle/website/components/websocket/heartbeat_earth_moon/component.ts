import { HeartbeatMonitorComponent, type HeartbeatMonitorConfig } from "../common/heartbeat_monitor.js";

const HEARTBEAT_EARTH_MOON_CONFIG: HeartbeatMonitorConfig = {
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
};

class HeartbeatEarthMoonComponent extends HeartbeatMonitorComponent {
    constructor(element: HTMLElement) {
        super(element, HEARTBEAT_EARTH_MOON_CONFIG);
    }
}

document.querySelectorAll<HTMLElement>(HEARTBEAT_EARTH_MOON_CONFIG.selector).forEach((element) => {
    new HeartbeatEarthMoonComponent(element);
});

