import { createPeriodicSender, type PeriodicTask } from "../base/component.js";
import { GpxWebSocketComponent } from "../../graphic/common/gpx.js";
import {
    createArcCurve,
    createSphereMesh,
    latLonToVector3,
    loadHdrTexture,
    loadTexture,
    loadThreeModule,
} from "../../graphic/common/threejs/index.js";
const MODULE_DIR_URL = new URL("./", import.meta.url);
const WEBSOCKET_COMPONENTS_URL = new URL("../", MODULE_DIR_URL);
const PAYLOAD_WORKER_URL = new URL("heartbeat_payload_worker.js", MODULE_DIR_URL).toString();
const EARTH_MOON_ASSET_BASE = new URL("heartbeat_earth_moon/assets", WEBSOCKET_COMPONENTS_URL).toString();
const EARTH_MOON_ASSETS = {
    earthMap: `${EARTH_MOON_ASSET_BASE}/earth_atmos_2048.jpg`,
    earthNormal: `${EARTH_MOON_ASSET_BASE}/earth_normal_2048.jpg`,
    earthSpecular: `${EARTH_MOON_ASSET_BASE}/earth_specular_2048.jpg`,
    moonMap: `${EARTH_MOON_ASSET_BASE}/moon_1024.jpg`,
    skyHdr: `${EARTH_MOON_ASSET_BASE}/HDR_silver_and_gold_nebulae.hdr`,
};

const EARTH_RADIUS_KM = 6371;
const MOON_RADIUS_KM = 1737.4;
const EARTH_TO_MOON_DISTANCE_KM = 384400;
const EARTH_SCENE_RADIUS = 0.82;
const SCENE_KM_PER_UNIT = EARTH_RADIUS_KM / EARTH_SCENE_RADIUS;
const MOON_SCENE_RADIUS = MOON_RADIUS_KM / SCENE_KM_PER_UNIT;
const COMPRESSED_DISTANCE_UNITS = (EARTH_TO_MOON_DISTANCE_KM / SCENE_KM_PER_UNIT) * 0.15;
const MAX_EMIT_PAYLOAD_BYTES = 64 * 1024 * 1024;

type NodeIcon = "dot" | "heart" | "moon";
type PlanetStyle = "earth" | "moon" | "earth_moon";

export type OrbitNode = {
    lat: number;
    lon: number;
    color: number;
    icon?: NodeIcon;
    label?: string;
};

export type HeartbeatMonitorConfig = {
    selector: string;
    toastSource: string;
    toastLabel: string;
    timeoutMessage: string;
    colors: {
        tx: number;
        rx: number;
    };
    labels?: {
        tx: string;
        rx: string;
    };
    planet: {
        style: PlanetStyle;
        rotationY: number;
        radius?: number;
    };
    nodes: {
        client: OrbitNode;
        server: OrbitNode;
    };
};

export class HeartbeatMonitorComponent extends GpxWebSocketComponent {
    connectionBadge: HTMLElement | null;
    directionBadge: HTMLElement | null;
    toggleButton: HTMLButtonElement | null;
    toggleLabel: HTMLElement | null;
    tempoInput: HTMLInputElement | null;
    tempoValue: HTMLElement | null;
    payloadInput: HTMLInputElement | null;
    payloadValue: HTMLElement | null;
    latencyMetric: HTMLElement | null;
    jitterMetric: HTMLElement | null;
    throughputMetric: HTMLElement | null;
    txRateMetric: HTMLElement | null;
    rxRateMetric: HTMLElement | null;
    totalSentMetric: HTMLElement | null;
    totalReceivedMetric: HTMLElement | null;
    encoder: TextEncoder;
    pending: boolean;
    lastSentAt: number | null;
    lastPayloadBytes: number;
    previousLatency: number | null;
    previousServerReceivedAt: number | null;
    previousServerTxBytes: number | null;
    previousServerRxBytes: number | null;
    totalSentPackets: number;
    totalReceivedPackets: number;
    totalSentBytes: number;
    totalReceivedBytes: number;
    idleTimer: number | null;
    timeoutTimer: number | null;
    startRequested: boolean;
    payloadCache: string;
    payloadCacheSize: number;
    payloadWorker: Worker | null;
    payloadBuildPending: boolean;
    payloadRequestId: number;
    payloadRequestSentAt: number | null;
    payloadBuildTimer: number | null;
    periodic: PeriodicTask;
    three: any;
    scene: any;
    camera: any;
    renderer: any;
    worldGroup: any;
    earthMesh: any;
    moonMesh: any;
    connectionArc: any;
    connectionArcRx: any;
    effects: any[];
    nodeVectors: { client: any; server: any } | null;
    earthMoonAnchors:
        | {
              clientTop: any;
              clientBottom: any;
              serverTop: any;
              serverBottom: any;
          }
        | null;
    earthMoonCenters: { earth: any; moon: any } | null;
    earthMoonRadii: { earth: number; moon: number } | null;
    animationFrame: number | null;
    resizeObserver: ResizeObserver | null;
    cameraRadius: number;
    cameraAzimuth: number;
    cameraPolar: number;
    cameraDragging: boolean;
    lastPointerX: number;
    lastPointerY: number;
    config: HeartbeatMonitorConfig;

    constructor(element: HTMLElement, config: HeartbeatMonitorConfig) {
        super(element);
        this.config = config;
        this.connectionBadge = element.querySelector('[data-role="connection"]');
        this.directionBadge = element.querySelector('[data-role="direction"]');
        this.toggleButton = element.querySelector('[data-action="toggle"]') as HTMLButtonElement | null;
        this.toggleLabel = element.querySelector('[data-role="toggle-label"]');
        this.tempoInput = element.querySelector('[data-control="tempo"]') as HTMLInputElement | null;
        this.tempoValue = element.querySelector('[data-control-value="tempo"]');
        this.payloadInput = element.querySelector('[data-control="payload"]') as HTMLInputElement | null;
        this.payloadValue = element.querySelector('[data-control-value="payload"]');
        this.latencyMetric = element.querySelector('[data-metric="latency"]');
        this.jitterMetric = element.querySelector('[data-metric="jitter"]');
        this.throughputMetric = element.querySelector('[data-metric="throughput"]');
        this.txRateMetric = element.querySelector('[data-metric="tx-rate"]');
        this.rxRateMetric = element.querySelector('[data-metric="rx-rate"]');
        this.totalSentMetric = element.querySelector('[data-metric="total-sent"]');
        this.totalReceivedMetric = element.querySelector('[data-metric="total-received"]');

        this.encoder = new TextEncoder();
        this.pending = false;
        this.lastSentAt = null;
        this.lastPayloadBytes = 0;
        this.previousLatency = null;
        this.previousServerReceivedAt = null;
        this.previousServerTxBytes = null;
        this.previousServerRxBytes = null;
        this.totalSentPackets = 0;
        this.totalReceivedPackets = 0;
        this.totalSentBytes = 0;
        this.totalReceivedBytes = 0;
        this.idleTimer = null;
        this.timeoutTimer = null;
        this.startRequested = false;
        this.payloadCache = "";
        this.payloadCacheSize = 0;
        this.payloadWorker = null;
        this.payloadBuildPending = false;
        this.payloadRequestId = 0;
        this.payloadRequestSentAt = null;
        this.payloadBuildTimer = null;
        this.periodic = createPeriodicSender(() => this.sendKeepalive());

        this.three = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.worldGroup = null;
        this.earthMesh = null;
        this.moonMesh = null;
        this.connectionArc = null;
        this.connectionArcRx = null;
        this.effects = [];
        this.nodeVectors = null;
        this.earthMoonAnchors = null;
        this.earthMoonCenters = null;
        this.earthMoonRadii = null;
        this.animationFrame = null;
        this.resizeObserver = null;
        this.cameraRadius = 4.4;
        this.cameraAzimuth = 0;
        this.cameraPolar = Math.PI / 2;
        this.cameraDragging = false;
        this.lastPointerX = 0;
        this.lastPointerY = 0;

        this.bind();
    }

    setConnection(state: string, label: string) {
        this.element.dataset.state = state;
        if (this.connectionBadge) {
            this.connectionBadge.textContent = label;
        }
        if (this.toggleButton) {
            this.toggleButton.disabled = state === "connecting";
        }
        this.setServerVisibility(state === "connected");
    }

    setServerVisibility(visible: boolean) {
        if (this.config.planet.style !== "earth_moon") {
            return;
        }
        if (this.moonMesh) {
            this.moonMesh.visible = visible;
        }
        if (this.connectionArc) {
            this.connectionArc.visible = visible;
        }
        if (this.connectionArcRx) {
            this.connectionArcRx.visible = visible;
        }
        if (!visible && this.effects.length > 0) {
            const keep: any[] = [];
            for (const item of this.effects) {
                const kind = item?.userData?.kind;
                if (kind === "beam-egg" || kind === "line" || kind === "arrow" || kind === "ring") {
                    item.parent?.remove(item);
                    item.geometry?.dispose?.();
                    item.material?.dispose?.();
                    continue;
                }
                keep.push(item);
            }
            this.effects = keep;
        }
    }

    setDirection(direction: string, label: string) {
        this.element.dataset.direction = direction;
        if (this.directionBadge) {
            this.directionBadge.textContent = label;
        }
    }

    pulseDirection(direction: string, label: string) {
        this.setDirection(direction, label);
        window.clearTimeout(this.idleTimer ?? undefined);
        this.idleTimer = window.setTimeout(() => this.setDirection("idle", "Idle"), 850);
    }

    getControlValue(input: HTMLInputElement | null, fallback: number) {
        if (!input) {
            return fallback;
        }
        const raw = Number.parseFloat(input.value || `${fallback}`);
        if (input.dataset.scale !== "log") {
            return Number.isFinite(raw) ? raw : fallback;
        }
        const minPos = Number.parseFloat(input.min || "0");
        const maxPos = Number.parseFloat(input.max || "100");
        const minValue = Number.parseFloat(input.dataset.minValue || "0");
        const maxValue = Number.parseFloat(input.dataset.maxValue || "0");
        if (
            !Number.isFinite(raw) ||
            !Number.isFinite(minPos) ||
            !Number.isFinite(maxPos) ||
            !Number.isFinite(minValue) ||
            !Number.isFinite(maxValue) ||
            minValue <= 0 ||
            maxValue <= minValue ||
            maxPos <= minPos
        ) {
            return fallback;
        }
        const clamped = Math.min(maxPos, Math.max(minPos, raw));
        const t = (clamped - minPos) / (maxPos - minPos);
        return minValue * Math.pow(maxValue / minValue, t);
    }

    updateTempoLabel() {
        if (!this.tempoValue) {
            return;
        }
        const seconds = this.getControlValue(this.tempoInput, 1);
        if (seconds < 1) {
            this.tempoValue.textContent = `${Math.round(seconds * 1000)}ms`;
            return;
        }
        this.tempoValue.textContent = `${seconds.toFixed(seconds < 10 ? 2 : 1)}s`;
    }

    getPayloadTargetBytes() {
        return Math.max(1024, Math.round(this.getControlValue(this.payloadInput, 1024)));
    }

    updatePayloadLabel() {
        if (!this.payloadValue || !this.payloadInput) {
            return;
        }
        const selected = this.getPayloadTargetBytes();
        if (selected <= MAX_EMIT_PAYLOAD_BYTES) {
            this.payloadValue.textContent = this.formatBytes(selected);
            return;
        }
        this.payloadValue.textContent = `${this.formatBytes(selected)} (send ${this.formatBytes(MAX_EMIT_PAYLOAD_BYTES)})`;
    }

    getTempoMs() {
        const seconds = this.getControlValue(this.tempoInput, 1);
        return Math.max(10, Math.round(seconds * 1000));
    }

    formatRate(bytes: number, elapsedMs: number) {
        const bytesPerSecond = (bytes / Math.max(elapsedMs, 1)) * 1000;
        if (bytesPerSecond < 1024) {
            return `${bytesPerSecond.toFixed(0)} B/s`;
        }
        if (bytesPerSecond < 1024 * 1024) {
            return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
        }
        if (bytesPerSecond < 1024 * 1024 * 1024) {
            return `${(bytesPerSecond / (1024 * 1024)).toFixed(2)} MB/s`;
        }
        return `${(bytesPerSecond / (1024 * 1024 * 1024)).toFixed(2)} GB/s`;
    }

    setRateMetrics(txBytesPerSecond: number, rxBytesPerSecond: number) {
        const tx = this.formatRate(txBytesPerSecond, 1000);
        const rx = this.formatRate(rxBytesPerSecond, 1000);
        if (this.txRateMetric) {
            this.txRateMetric.textContent = `TX: ${tx}`;
        }
        if (this.rxRateMetric) {
            this.rxRateMetric.textContent = `RX: ${rx}`;
        }
        if (this.throughputMetric) {
            this.throughputMetric.textContent = `${tx} / ${rx}`;
        }
    }

    serverTimestampToMs(value: number) {
        // Backward compatible: treat very large values as nanoseconds epoch.
        if (value > 1_000_000_000_000_000) {
            return value / 1_000_000;
        }
        return value;
    }

    formatBytes(bytes: number) {
        const units = ["B", "KB", "MB", "GB"];
        let value = Math.max(0, bytes);
        let unitIndex = 0;
        while (value >= 1024 && unitIndex < units.length - 1) {
            value /= 1024;
            unitIndex += 1;
        }
        const precision = unitIndex === 0 ? 0 : value < 10 ? 2 : 1;
        return `${value.toFixed(precision)} ${units[unitIndex]}`;
    }

    updateTotals() {
        if (this.totalSentMetric) {
            this.totalSentMetric.textContent = `${this.formatBytes(this.totalSentBytes)} (${this.totalSentPackets} pkgs)`;
        }
        if (this.totalReceivedMetric) {
            this.totalReceivedMetric.textContent = `${this.formatBytes(this.totalReceivedBytes)} (${this.totalReceivedPackets} pkgs)`;
        }
    }

    updateMetrics(latencyMs: number, downloadBytes: number, updateRates = true) {
        const jitter = this.previousLatency == null ? 0 : Math.abs(latencyMs - this.previousLatency);
        this.previousLatency = latencyMs;

        if (this.latencyMetric) {
            this.latencyMetric.textContent = `${Math.round(latencyMs)} ms`;
        }
        if (this.jitterMetric) {
            this.jitterMetric.textContent = `${Math.round(jitter)} ms`;
        }
        if (updateRates) {
            this.setRateMetrics((this.lastPayloadBytes / Math.max(latencyMs, 1)) * 1000, (downloadBytes / Math.max(latencyMs, 1)) * 1000);
        }
        this.updateTotals();
    }

    sendKeepalive() {
        if (!this.channel || !this.isOpen() || this.pending || this.payloadBuildPending) {
            return false;
        }
        const sentAt = Date.now();
        const payloadTargetBytes = Math.min(this.getPayloadTargetBytes(), MAX_EMIT_PAYLOAD_BYTES);
        if (this.payloadWorker) {
            this.payloadBuildPending = true;
            this.payloadRequestId += 1;
            this.payloadRequestSentAt = sentAt;
            window.clearTimeout(this.payloadBuildTimer ?? undefined);
            this.payloadBuildTimer = window.setTimeout(() => {
                if (!this.payloadBuildPending || this.payloadRequestSentAt == null) {
                    return;
                }
                this.payloadBuildPending = false;
                const fallbackSentAt = this.payloadRequestSentAt;
                this.payloadRequestSentAt = null;
                const payload = this.buildKeepalivePayload(fallbackSentAt, payloadTargetBytes);
                const raw = JSON.stringify(payload);
                this.sendKeepaliveRaw(raw, fallbackSentAt);
            }, 3000);
            this.payloadWorker.postMessage({
                id: this.payloadRequestId,
                sentAt,
                payloadTargetBytes,
            });
            return true;
        }
        const payload = this.buildKeepalivePayload(sentAt, payloadTargetBytes);
        const raw = JSON.stringify(payload);
        return this.sendKeepaliveRaw(raw, sentAt);
    }

    buildKeepalivePayload(sentAt: number, payloadTargetBytes: number) {
        const base = { type: "keepalive", sent_at: sentAt, payload: "" };
        if (payloadTargetBytes <= 0) {
            return { type: "keepalive", sent_at: sentAt };
        }
        const baseRawSize = this.encoder.encode(JSON.stringify(base)).length;
        const contentBytes = Math.max(0, payloadTargetBytes - baseRawSize);
        if (contentBytes > this.payloadCacheSize) {
            const seed = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
            let cache = this.payloadCache;
            while (cache.length < contentBytes) {
                const needed = contentBytes - cache.length;
                cache += needed >= seed.length ? seed : seed.slice(0, needed);
            }
            this.payloadCache = cache;
            this.payloadCacheSize = cache.length;
        }
        return { type: "keepalive", sent_at: sentAt, payload: this.payloadCache.slice(0, contentBytes) };
    }

    sendKeepaliveRaw(raw: string, sentAt: number) {
        if (!this.send(raw)) {
            return false;
        }
        this.pending = true;
        this.lastSentAt = sentAt;
        this.lastPayloadBytes = this.encoder.encode(raw).length;
        this.totalSentPackets += 1;
        this.totalSentBytes += this.lastPayloadBytes;
        this.updateTotals();
        this.pulseDirection("tx", this.config.labels?.tx ?? "TX");
        this.spawnPulse("tx");

        window.clearTimeout(this.timeoutTimer ?? undefined);
        this.timeoutTimer = window.setTimeout(() => {
            if (!this.pending) {
                return;
            }
            this.pending = false;
            this.setDirection("idle", "Timeout");
        }, 3200);
        return true;
    }

    initPayloadWorker() {
        if (typeof Worker === "undefined") {
            return;
        }
        try {
            this.payloadWorker = new Worker(PAYLOAD_WORKER_URL, { type: "module" });
        } catch {
            this.payloadWorker = null;
            return;
        }
        this.payloadWorker.addEventListener("message", (event) => {
            const detail = event.data as { id?: number; raw?: string } | undefined;
            if (!detail || typeof detail.id !== "number" || typeof detail.raw !== "string") {
                return;
            }
            if (detail.id !== this.payloadRequestId || this.payloadRequestSentAt == null) {
                return;
            }
            window.clearTimeout(this.payloadBuildTimer ?? undefined);
            this.payloadBuildTimer = null;
            this.payloadBuildPending = false;
            const sentAt = this.payloadRequestSentAt;
            this.payloadRequestSentAt = null;
            if (!this.isOpen() || this.pending) {
                return;
            }
            this.sendKeepaliveRaw(detail.raw, sentAt);
        });
        this.payloadWorker.addEventListener("error", () => {
            this.payloadWorker?.terminate();
            this.payloadWorker = null;
            window.clearTimeout(this.payloadBuildTimer ?? undefined);
            this.payloadBuildTimer = null;
            this.payloadBuildPending = false;
            this.payloadRequestSentAt = null;
        });
    }

    stopLoop() {
        window.clearTimeout(this.payloadBuildTimer ?? undefined);
        this.payloadBuildTimer = null;
        this.payloadBuildPending = false;
        this.payloadRequestSentAt = null;
        this.pending = false;
        this.periodic.stop();
        window.clearTimeout(this.timeoutTimer ?? undefined);
        window.clearTimeout(this.idleTimer ?? undefined);
        if (this.toggleLabel) {
            this.toggleLabel.textContent = "Start Sweep";
        }
    }

    stopAll() {
        this.startRequested = false;
        this.stopLoop();
        this.channel?.close();
        this.setDirection("idle", "Idle");
        this.setConnection("disconnected", "Stopped");
    }

    startLoop() {
        this.startRequested = true;
        this.channel?.connect();
        if (this.isOpen()) {
            this.periodic.start(Infinity, this.getTempoMs());
            if (this.toggleLabel) {
                this.toggleLabel.textContent = "Stop Sweep";
            }
        }
    }

    toggleLoop() {
        if (this.periodic.isRunning()) {
            this.stopAll();
            return;
        }
        this.startLoop();
    }

    latLonToVector3(lat: number, lon: number, radius: number) {
        return latLonToVector3(this.three, lat, lon, radius);
    }

    createIconSprite(icon: NodeIcon, colorHex: string) {
        const canvas = document.createElement("canvas");
        canvas.width = 128;
        canvas.height = 128;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
            return null;
        }
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = "88px 'Segoe UI Symbol', 'Segoe UI Emoji', sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = colorHex;
        if (icon === "heart") {
            ctx.fillText("\u2665", 64, 64);
        } else if (icon === "moon") {
            ctx.fillText("\u263E", 64, 64);
        } else {
            ctx.fillText("\u25CF", 64, 64);
        }
        const texture = new this.three.CanvasTexture(canvas);
        texture.needsUpdate = true;
        return texture;
    }

    createAuraTexture(colorHex: string) {
        const canvas = document.createElement("canvas");
        canvas.width = 256;
        canvas.height = 256;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
            return null;
        }
        const gradient = ctx.createRadialGradient(128, 128, 12, 128, 128, 124);
        gradient.addColorStop(0, `${colorHex}cc`);
        gradient.addColorStop(0.45, `${colorHex}55`);
        gradient.addColorStop(1, `${colorHex}00`);
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        const texture = new this.three.CanvasTexture(canvas);
        texture.needsUpdate = true;
        return texture;
    }

    spawnNode(position: any, node: OrbitNode) {
        const icon = node.icon ?? "dot";
        if (this.config.planet.style === "earth_moon" && icon === "moon") {
            return;
        }
        if (icon === "dot") {
            const material = new this.three.MeshBasicMaterial({ color: node.color });
            const marker = createSphereMesh(this.three, 0.035, 16, 16, material);
            marker.position.copy(position);
            this.worldGroup.add(marker);
            return;
        }

        const colorHex = `#${node.color.toString(16).padStart(6, "0")}`;
        const texture = this.createIconSprite(icon, colorHex);
        if (!texture) {
            return;
        }
        const material = new this.three.SpriteMaterial({
            map: texture,
            transparent: true,
            depthWrite: false,
            sizeAttenuation: true,
        });
        const sprite = new this.three.Sprite(material);
        if (this.config.planet.style === "earth_moon") {
            sprite.position.copy(position);
        } else {
            sprite.position.copy(position.clone().multiplyScalar(1.03));
        }
        sprite.scale.set(0.28, 0.28, 0.28);
        this.worldGroup.add(sprite);

        if (icon === "heart") {
            const auraTexture = this.createAuraTexture(colorHex);
            if (auraTexture) {
                const auraMaterial = new this.three.SpriteMaterial({
                    map: auraTexture,
                    transparent: true,
                    depthWrite: false,
                    sizeAttenuation: true,
                    blending: this.three.AdditiveBlending,
                });
                const aura = new this.three.Sprite(auraMaterial);
                aura.position.copy(sprite.position);
                aura.scale.set(0.42, 0.42, 0.42);
                aura.userData = { born: performance.now(), ttl: Number.POSITIVE_INFINITY, kind: "heart-aura" };
                this.effects.push(aura);
                this.worldGroup.add(aura);
            }
        }
    }

    spawnRing(position: any, color: number, normal?: any) {
        const geometry = new this.three.RingGeometry(0.02, 0.05, 30);
        const material = new this.three.MeshBasicMaterial({
            color,
            transparent: true,
            opacity: 0.7,
            side: this.three.DoubleSide,
        });
        const ring = new this.three.Mesh(geometry, material);
        const facing = (normal ?? position).clone().normalize();
        ring.quaternion.setFromUnitVectors(new this.three.Vector3(0, 0, 1), facing);
        ring.position.copy(position);
        ring.userData = { born: performance.now(), ttl: 900, kind: "ring" };
        this.effects.push(ring);
        this.worldGroup.add(ring);
    }

    createPulseCurve(start: any, end: any, direction: "tx" | "rx") {
        if (this.config.planet.style === "earth_moon" && this.earthMoonCenters) {
            const earthCenter = this.earthMoonCenters.earth;
            const moonCenter = this.earthMoonCenters.moon;
            const startEarthDistance = start.distanceTo(earthCenter);
            const startMoonDistance = start.distanceTo(moonCenter);
            const endEarthDistance = end.distanceTo(earthCenter);
            const endMoonDistance = end.distanceTo(moonCenter);

            const startCenter = startEarthDistance <= startMoonDistance ? earthCenter : moonCenter;
            const endCenter = endEarthDistance <= endMoonDistance ? earthCenter : moonCenter;

            const startNormal = start.clone().sub(startCenter).normalize();
            const endNormal = end.clone().sub(endCenter).normalize();
            const separation = start.distanceTo(end);
            const handle = separation * 0.28;

            const c1 = start.clone().add(startNormal.multiplyScalar(handle));
            const c2 = end.clone().add(endNormal.multiplyScalar(handle));
            return new this.three.CubicBezierCurve3(start.clone(), c1, c2, end.clone());
        }

        return createArcCurve(this.three, start, end, { lift: 0.48 });
    }

    spawnPulse(direction: "tx" | "rx") {
        if (!this.three || !this.worldGroup || !this.nodeVectors) {
            return;
        }
        if (this.config.planet.style === "earth_moon" && this.moonMesh && !this.moonMesh.visible) {
            return;
        }
        const tx = direction === "tx";
        let start = tx ? this.nodeVectors.client : this.nodeVectors.server;
        let end = tx ? this.nodeVectors.server : this.nodeVectors.client;
        if (this.config.planet.style === "earth_moon" && this.earthMoonAnchors) {
            if (tx) {
                start = this.earthMoonAnchors.clientTop;
                end = this.earthMoonAnchors.serverTop;
            } else {
                start = this.earthMoonAnchors.serverBottom;
                end = this.earthMoonAnchors.clientBottom;
            }
        }
        const color = tx ? this.config.colors.tx : this.config.colors.rx;

        const curve = this.createPulseCurve(start, end, direction);
        if (this.config.planet.style === "earth_moon") {
            const beam = new this.three.Mesh(
                new this.three.SphereGeometry(0.12, 20, 20),
                new this.three.MeshBasicMaterial({
                    color,
                    transparent: true,
                    opacity: 0.72,
                    blending: this.three.AdditiveBlending,
                    depthWrite: false,
                })
            );
            beam.scale.set(0.72, 1.28, 0.72);
            beam.userData = { born: performance.now(), ttl: 820, kind: "beam-egg", curve };
            this.effects.push(beam);
            this.worldGroup.add(beam);
            return;
        }

        const points = curve.getPoints(64);
        const geometry = new this.three.BufferGeometry().setFromPoints(points);
        const material = new this.three.LineBasicMaterial({ color, transparent: true, opacity: 0.96 });
        const line = new this.three.Line(geometry, material);
        line.userData = { born: performance.now(), ttl: 1000, kind: "line" };
        this.effects.push(line);
        this.worldGroup.add(line);

        const arrowRadius = 0.03;
        const arrowLength = 0.12;
        const arrow = new this.three.Mesh(
            new this.three.ConeGeometry(arrowRadius, arrowLength, 12),
            new this.three.MeshBasicMaterial({ color, transparent: true, opacity: 0.95 })
        );
        arrow.userData = { born: performance.now(), ttl: 1000, kind: "arrow", curve };
        this.effects.push(arrow);
        this.worldGroup.add(arrow);

        this.spawnRing(end.clone(), color);
    }

    ensureConnectionArc() {
        if (!this.three || !this.worldGroup || !this.nodeVectors || !this.earthMoonAnchors || this.config.planet.style !== "earth_moon") {
            return;
        }
        if (!this.connectionArc) {
            const curveTx = this.createPulseCurve(this.earthMoonAnchors.clientTop, this.earthMoonAnchors.serverTop, "tx");
            const pointsTx = curveTx.getPoints(96);
            const geometryTx = new this.three.BufferGeometry().setFromPoints(pointsTx);
            const materialTx = new this.three.LineBasicMaterial({
                color: 0xf8fafc,
                transparent: true,
                opacity: 0.22,
            });
            this.connectionArc = new this.three.Line(geometryTx, materialTx);
            this.worldGroup.add(this.connectionArc);
        }
        if (!this.connectionArcRx) {
            const curveRx = this.createPulseCurve(this.earthMoonAnchors.serverBottom, this.earthMoonAnchors.clientBottom, "rx");
            const pointsRx = curveRx.getPoints(96);
            const geometryRx = new this.three.BufferGeometry().setFromPoints(pointsRx);
            const materialRx = new this.three.LineBasicMaterial({
                color: 0xf8fafc,
                transparent: true,
                opacity: 0.26,
            });
            this.connectionArcRx = new this.three.Line(geometryRx, materialRx);
            this.worldGroup.add(this.connectionArcRx);
        }
    }

    resizeRenderer() {
        if (!this.renderer || !this.camera || !this.canvas) {
            return;
        }
        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;
        this.renderer.setSize(width, height, false);
        this.camera.aspect = width / Math.max(height, 1);
        this.camera.updateProjectionMatrix();
    }

    updateCameraPosition() {
        if (!this.camera) {
            return;
        }
        const sinPolar = Math.sin(this.cameraPolar);
        const x = this.cameraRadius * sinPolar * Math.cos(this.cameraAzimuth);
        const y = this.cameraRadius * Math.cos(this.cameraPolar);
        const z = this.cameraRadius * sinPolar * Math.sin(this.cameraAzimuth);
        this.camera.position.set(x, y, z);
        this.camera.lookAt(0, 0, 0);
    }

    bindCameraControls() {
        if (!this.canvas) {
            return;
        }
        this.canvas.style.touchAction = "none";
        this.canvas.addEventListener("pointerdown", (event) => {
            this.cameraDragging = true;
            this.lastPointerX = event.clientX;
            this.lastPointerY = event.clientY;
            this.canvas?.setPointerCapture(event.pointerId);
        });
        this.canvas.addEventListener("pointermove", (event) => {
            if (!this.cameraDragging) {
                return;
            }
            const dx = event.clientX - this.lastPointerX;
            const dy = event.clientY - this.lastPointerY;
            this.lastPointerX = event.clientX;
            this.lastPointerY = event.clientY;
            this.cameraAzimuth -= dx * 0.01;
            this.cameraPolar = Math.min(Math.PI - 0.12, Math.max(0.12, this.cameraPolar + dy * 0.01));
            this.updateCameraPosition();
        });
        const stopDrag = (pointerId?: number) => {
            this.cameraDragging = false;
            if (pointerId != null) {
                this.canvas?.releasePointerCapture(pointerId);
            }
        };
        this.canvas.addEventListener("pointerup", (event) => stopDrag(event.pointerId));
        this.canvas.addEventListener("pointercancel", (event) => stopDrag(event.pointerId));
        this.canvas.addEventListener("pointerleave", () => stopDrag());
        this.canvas.addEventListener("wheel", (event) => {
            event.preventDefault();
            const minRadius = this.config.planet.style === "earth_moon" ? 4.5 : 2.1;
            const maxRadius = this.config.planet.style === "earth_moon" ? 18 : 6.2;
            this.cameraRadius = Math.min(maxRadius, Math.max(minRadius, this.cameraRadius + event.deltaY * 0.003));
            this.updateCameraPosition();
        });
    }

    sampleNoise(x: number, y: number, seed: number) {
        const v =
            Math.sin((x + seed) * 3.1) * Math.cos((y - seed) * 2.7) +
            0.6 * Math.sin((x + y + seed * 0.7) * 5.2) +
            0.3 * Math.cos((x * 1.7 - y * 1.3 + seed) * 9.1);
        return v;
    }

    createEarthTexture(THREE: any) {
        const canvas = document.createElement("canvas");
        canvas.width = 1024;
        canvas.height = 512;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
            return null;
        }

        const ocean = ctx.createLinearGradient(0, 0, 0, canvas.height);
        ocean.addColorStop(0, "#0a2f6e");
        ocean.addColorStop(0.5, "#0d4ca6");
        ocean.addColorStop(1, "#0a3a82");
        ctx.fillStyle = ocean;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = image.data;
        for (let py = 0; py < canvas.height; py += 1) {
            for (let px = 0; px < canvas.width; px += 1) {
                const nx = px / canvas.width;
                const ny = py / canvas.height;
                const n = this.sampleNoise(nx * 2 - 1, ny * 2 - 1, 0.37);
                const i = (py * canvas.width + px) * 4;
                if (n > 0.35) {
                    data[i] = 48;
                    data[i + 1] = 120 + Math.floor((n - 0.35) * 110);
                    data[i + 2] = 48;
                } else if (n > 0.29) {
                    data[i] = 188;
                    data[i + 1] = 165;
                    data[i + 2] = 102;
                } else {
                    const ripple = Math.floor((n + 1.5) * 18);
                    data[i] = Math.min(255, data[i] + ripple);
                    data[i + 1] = Math.min(255, data[i + 1] + ripple);
                    data[i + 2] = Math.min(255, data[i + 2] + ripple * 2);
                }
            }
        }
        ctx.putImageData(image, 0, 0);

        ctx.fillStyle = "rgba(255, 255, 255, 0.14)";
        for (let i = 0; i < 120; i += 1) {
            const x = Math.random() * canvas.width;
            const y = Math.random() * canvas.height;
            const r = 14 + Math.random() * 42;
            ctx.beginPath();
            ctx.ellipse(x, y, r * 1.5, r, Math.random() * Math.PI, 0, Math.PI * 2);
            ctx.fill();
        }

        const texture = new THREE.CanvasTexture(canvas);
        texture.wrapS = THREE.ClampToEdgeWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;
        texture.needsUpdate = true;
        return texture;
    }

    createMoonTexture(THREE: any) {
        const canvas = document.createElement("canvas");
        canvas.width = 1024;
        canvas.height = 512;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
            return null;
        }
        ctx.fillStyle = "#a5adb8";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        for (let i = 0; i < 420; i += 1) {
            const x = Math.random() * canvas.width;
            const y = Math.random() * canvas.height;
            const r = 2 + Math.random() * 16;
            ctx.fillStyle = "rgba(108, 117, 128, 0.45)";
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = "rgba(203, 213, 225, 0.25)";
            ctx.lineWidth = Math.max(1, r * 0.12);
            ctx.stroke();
        }

        const texture = new THREE.CanvasTexture(canvas);
        texture.wrapS = THREE.ClampToEdgeWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;
        texture.needsUpdate = true;
        return texture;
    }

    async loadEarthMoonAssets(THREE: any) {
        const [earthMap, earthNormal, earthSpecular, moonMap, skyHdr] = await Promise.all([
            loadTexture(THREE, EARTH_MOON_ASSETS.earthMap, (texture) => {
                texture.colorSpace = THREE.SRGBColorSpace;
                texture.anisotropy = 8;
            }),
            loadTexture(THREE, EARTH_MOON_ASSETS.earthNormal, (texture) => {
                texture.anisotropy = 8;
            }),
            loadTexture(THREE, EARTH_MOON_ASSETS.earthSpecular, (texture) => {
                texture.anisotropy = 8;
            }),
            loadTexture(THREE, EARTH_MOON_ASSETS.moonMap, (texture) => {
                texture.colorSpace = THREE.SRGBColorSpace;
                texture.anisotropy = 8;
            }),
            loadHdrTexture(EARTH_MOON_ASSETS.skyHdr),
        ]);

        return { earthMap, earthNormal, earthSpecular, moonMap, skyHdr };
    }

    addPlanet(THREE: any, assets?: any) {
        const radius = this.config.planet.radius ?? 1;
        if (this.config.planet.style === "earth_moon") {
            const earthRadius = EARTH_SCENE_RADIUS;
            const moonRadius = MOON_SCENE_RADIUS;
            const earthPosition = new THREE.Vector3(-COMPRESSED_DISTANCE_UNITS * 0.5, 0, 0);
            const moonPosition = new THREE.Vector3(COMPRESSED_DISTANCE_UNITS * 0.5, 0, 0);

            const earth = new THREE.Mesh(
                new THREE.SphereGeometry(earthRadius, 64, 64),
                new THREE.MeshPhongMaterial({
                    color: 0xffffff,
                    emissive: 0x030812,
                    shininess: 28,
                    specular: 0x2f4f7f,
                    map: assets?.earthMap ?? this.createEarthTexture(THREE),
                    normalMap: assets?.earthNormal ?? null,
                    specularMap: assets?.earthSpecular ?? null,
                })
            );
            earth.scale.set(1, 0.9966, 1);
            earth.position.copy(earthPosition);
            this.worldGroup.add(earth);
            this.earthMesh = earth;

            const atmosphere = new THREE.Mesh(
                new THREE.SphereGeometry(earthRadius * 1.08, 44, 44),
                new THREE.MeshBasicMaterial({
                    color: 0x38bdf8,
                    transparent: true,
                    opacity: 0.09,
                    side: THREE.BackSide,
                })
            );
            atmosphere.position.copy(earthPosition);
            this.worldGroup.add(atmosphere);

            const moon = new THREE.Mesh(
                new THREE.SphereGeometry(moonRadius, 40, 40),
                new THREE.MeshStandardMaterial({
                    color: 0xf1f5f9,
                    emissive: 0x05080f,
                    metalness: 0.02,
                    roughness: 0.95,
                    map: assets?.moonMap ?? this.createMoonTexture(THREE),
                    bumpMap: assets?.moonMap ?? null,
                    bumpScale: moonRadius * 0.04,
                })
            );
            moon.position.copy(moonPosition);
            this.worldGroup.add(moon);
            this.moonMesh = moon;

            this.earthMoonCenters = { earth: earthPosition, moon: moonPosition };
            this.earthMoonRadii = { earth: earthRadius, moon: moonRadius };
            const clientTop = earthPosition.clone().add(new THREE.Vector3(0, earthRadius * earth.scale.y, 0));
            const clientBottom = earthPosition.clone().add(new THREE.Vector3(0, -earthRadius * earth.scale.y, 0));
            const serverTop = moonPosition.clone().add(new THREE.Vector3(0, moonRadius * moon.scale.y, 0));
            const serverBottom = moonPosition.clone().add(new THREE.Vector3(0, -moonRadius * moon.scale.y, 0));
            this.earthMoonAnchors = { clientTop, clientBottom, serverTop, serverBottom };
            return;
        }

        if (this.config.planet.style === "moon") {
            const moon = new THREE.Mesh(
                new THREE.SphereGeometry(radius, 56, 56),
                new THREE.MeshStandardMaterial({
                    color: 0xb8c0cc,
                    emissive: 0x111827,
                    metalness: 0.12,
                    roughness: 0.92,
                    map: this.createMoonTexture(THREE),
                })
            );
            this.worldGroup.add(moon);

            for (let i = 0; i < 20; i += 1) {
                const crater = new THREE.Mesh(
                    new THREE.SphereGeometry(0.035 + Math.random() * 0.02, 10, 10),
                    new THREE.MeshStandardMaterial({ color: 0x8e97a6, roughness: 0.95, metalness: 0.05 })
                );
                const lat = -70 + Math.random() * 140;
                const lon = -180 + Math.random() * 360;
                const p = this.latLonToVector3(lat, lon, radius * 1.002);
                crater.position.copy(p);
                crater.scale.set(1, 0.4 + Math.random() * 0.4, 1);
                crater.lookAt(new THREE.Vector3(0, 0, 0));
                this.worldGroup.add(crater);
            }
            return;
        }

        const earth = new THREE.Mesh(
            new THREE.SphereGeometry(radius, 64, 64),
            new THREE.MeshStandardMaterial({
                color: 0x12345f,
                emissive: 0x0a1b34,
                metalness: 0.28,
                roughness: 0.56,
                map: this.createEarthTexture(THREE),
            })
        );
        this.worldGroup.add(earth);

        const atmosphere = new THREE.Mesh(
            new THREE.SphereGeometry(radius * 1.08, 40, 40),
            new THREE.MeshBasicMaterial({
                color: 0x7dd3fc,
                transparent: true,
                opacity: 0.09,
                side: THREE.BackSide,
            })
        );
        this.worldGroup.add(atmosphere);
    }

    async initThree() {
        if (!this.canvas || this.renderer) {
            return;
        }
        try {
            this.three = await loadThreeModule();
        } catch {
            this.setConnection("disconnected", "3D Unavailable");
            return;
        }

        const THREE = this.three;
        const isEarthMoon = this.config.planet.style === "earth_moon";
        const earthMoonAssets = isEarthMoon ? await this.loadEarthMoonAssets(THREE) : null;
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
        if (isEarthMoon) {
            this.cameraRadius = 9.2;
        }
        this.updateCameraPosition();

        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true,
        });
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = isEarthMoon ? 1.58 : 1;
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.resizeRenderer();
        if (isEarthMoon && earthMoonAssets?.skyHdr) {
            earthMoonAssets.skyHdr.mapping = THREE.EquirectangularReflectionMapping;
            const pmremGenerator = new THREE.PMREMGenerator(this.renderer);
            pmremGenerator.compileEquirectangularShader();
            const envTarget = pmremGenerator.fromEquirectangular(earthMoonAssets.skyHdr);
            this.scene.background = earthMoonAssets.skyHdr;
            this.scene.environment = envTarget.texture;
            this.scene.backgroundBlurriness = 0;
            this.scene.backgroundIntensity = 1.45;
            earthMoonAssets.skyHdr.dispose?.();
            pmremGenerator.dispose();
        }

        if (this.config.planet.style === "moon") {
            const ambient = new THREE.AmbientLight(0xe2e8f0, 0.45);
            const rimLight = new THREE.DirectionalLight(0xf8fafc, 0.82);
            rimLight.position.set(2.2, 1.2, 2);
            const fillLight = new THREE.DirectionalLight(0x94a3b8, 0.4);
            fillLight.position.set(-2, -1.4, -1.4);
            this.scene.add(ambient, rimLight, fillLight);
        } else if (this.config.planet.style === "earth_moon") {
            const ambient = new THREE.AmbientLight(0xcbd5e1, 0.34);
            const sunLight = new THREE.DirectionalLight(0xf8fafc, 1.35);
            sunLight.position.set(8, 2.8, 1.2);
            const rimLight = new THREE.DirectionalLight(0xbfdbfe, 0.55);
            rimLight.position.set(-4, -1.6, -2.8);
            this.scene.add(ambient, sunLight, rimLight);
        } else {
            const ambient = new THREE.AmbientLight(0x8fdfff, 0.55);
            const rimLight = new THREE.DirectionalLight(0x66e5ff, 0.65);
            rimLight.position.set(2.2, 1.2, 2);
            const fillLight = new THREE.DirectionalLight(0x3b82f6, 0.5);
            fillLight.position.set(-2, -1.4, -1.4);
            this.scene.add(ambient, rimLight, fillLight);
        }

        this.worldGroup = new THREE.Group();
        this.scene.add(this.worldGroup);
        this.addPlanet(THREE, earthMoonAssets);

        const radius = (this.config.planet.radius ?? 1) * 1.03;
        let client = this.latLonToVector3(this.config.nodes.client.lat, this.config.nodes.client.lon, radius);
        let server = this.latLonToVector3(this.config.nodes.server.lat, this.config.nodes.server.lon, radius);
        if (this.config.planet.style === "earth_moon" && this.earthMoonAnchors) {
            client = this.earthMoonAnchors.clientTop.clone();
            server = this.earthMoonAnchors.serverTop.clone();
        }
        this.nodeVectors = { client, server };
        this.spawnNode(client, this.config.nodes.client);
        this.spawnNode(server, this.config.nodes.server);
        this.ensureConnectionArc();
        this.setServerVisibility(this.isOpen());

        this.resizeObserver = new ResizeObserver(() => this.resizeRenderer());
        this.resizeObserver.observe(this.canvas);
        this.bindCameraControls();
        this.animate();
    }

    animate() {
        if (!this.renderer || !this.scene || !this.camera || !this.worldGroup || !this.three) {
            return;
        }
        const now = performance.now();

        const alive = [];
        for (const item of this.effects) {
            const elapsed = now - item.userData.born;
            const progress = elapsed / item.userData.ttl;
            if (progress >= 1) {
                item.parent?.remove(item);
                item.geometry?.dispose?.();
                item.material?.dispose?.();
                continue;
            }
            const material = item.material;
            if (material && "opacity" in material) {
                material.opacity = Math.max(0, 1 - progress);
            }
            if (item.userData.kind === "line" && item.geometry?.setDrawRange) {
                const points = item.geometry.attributes?.position?.count ?? 0;
                const drawCount = Math.max(2, Math.floor(points * progress));
                item.geometry.setDrawRange(0, drawCount);
            }
            if (item.userData.kind === "ring") {
                const scale = 1 + progress * 5;
                item.scale.setScalar(scale);
            }
            if (item.userData.kind === "arrow" && item.userData.curve) {
                const t = Math.min(0.999, progress);
                const point = item.userData.curve.getPointAt(t);
                const nextPoint = item.userData.curve.getPointAt(Math.min(0.999, t + 0.02));
                item.position.copy(point);
                const tangent = nextPoint.clone().sub(point).normalize();
                item.quaternion.setFromUnitVectors(new this.three.Vector3(0, 1, 0), tangent);
            }
            if (item.userData.kind === "beam-egg" && item.userData.curve) {
                const t = Math.min(0.999, progress);
                const point = item.userData.curve.getPointAt(t);
                const nextPoint = item.userData.curve.getPointAt(Math.min(0.999, t + 0.02));
                item.position.copy(point);
                const tangent = nextPoint.clone().sub(point).normalize();
                item.quaternion.setFromUnitVectors(new this.three.Vector3(0, 1, 0), tangent);
                const pulse = 0.84 + 0.16 * Math.sin(now * 0.03);
                item.scale.set(0.72 * pulse, 1.28 * pulse, 0.72 * pulse);
                if (material && "opacity" in material) {
                    material.opacity = Math.max(0.12, 0.78 - progress * 0.5);
                }
            }
            if (item.userData.kind === "heart-aura") {
                const pulse = 0.5 + 0.5 * Math.sin(now * 0.006);
                const scale = 1 + pulse * 0.14;
                item.scale.set(0.42 * scale, 0.42 * scale, 0.42 * scale);
                if (material && "opacity" in material) {
                    material.opacity = 0.35 + pulse * 0.3;
                }
            }
            alive.push(item);
        }
        this.effects = alive;

        this.renderer.render(this.scene, this.camera);
        this.animationFrame = window.requestAnimationFrame(() => this.animate());
    }

    connectChannel() {
        this.channel = this.connect();
        if (!this.channel) {
            return;
        }

        this.on("connecting", () => {
            this.setConnection("connecting", "Connecting");
        });

        this.on("open", () => {
            this.setConnection("connected", "Connected");
            if (this.startRequested) {
                this.periodic.start(Infinity, this.getTempoMs());
                if (this.toggleLabel) {
                    this.toggleLabel.textContent = "Stop Sweep";
                }
            }
        });

        this.on("message", (event) => {
            const payload = event.detail?.data as
                | {
                      type?: string;
                      sent_at?: number;
                      received_at?: number;
                      server_rx_packets?: number;
                      server_tx_packets?: number;
                      server_rx_bytes?: number;
                      server_tx_bytes?: number;
                      request_frame_bytes?: number;
                      ack_frame_bytes?: number;
                  }
                | undefined;
            if (!payload || payload.type !== "keepalive_ack" || !this.pending) {
                return;
            }
            if (typeof payload.sent_at !== "number" || payload.sent_at !== this.lastSentAt) {
                return;
            }
            this.pending = false;
            const now = Date.now();
            const latencyMs = Math.max(1, now - payload.sent_at);
            const rawText = typeof event.detail?.raw === "string" ? event.detail.raw : "";
            const downloadBytes = this.encoder.encode(rawText).length;
            const hasServerTotals =
                typeof payload.server_rx_packets === "number" &&
                typeof payload.server_tx_packets === "number" &&
                typeof payload.server_rx_bytes === "number" &&
                typeof payload.server_tx_bytes === "number" &&
                typeof payload.received_at === "number";

            if (hasServerTotals) {
                this.totalSentPackets = Math.max(0, payload.server_rx_packets ?? 0);
                this.totalSentBytes = Math.max(0, payload.server_rx_bytes ?? 0);
                this.totalReceivedPackets = Math.max(0, payload.server_tx_packets ?? 0);
                this.totalReceivedBytes = Math.max(0, payload.server_tx_bytes ?? 0);

                const prevAt = this.previousServerReceivedAt;
                const prevTxBytes = this.previousServerTxBytes;
                const prevRxBytes = this.previousServerRxBytes;
                const currentAt = this.serverTimestampToMs(payload.received_at ?? now);
                const currentTxBytes = payload.server_tx_bytes ?? 0;
                const currentRxBytes = payload.server_rx_bytes ?? 0;

                if (
                    prevAt != null &&
                    prevTxBytes != null &&
                    prevRxBytes != null &&
                    currentAt > prevAt &&
                    currentTxBytes >= prevTxBytes &&
                    currentRxBytes >= prevRxBytes
                ) {
                    const elapsedMs = currentAt - prevAt;
                    const rxBytesPerSecond = ((currentTxBytes - prevTxBytes) / elapsedMs) * 1000;
                    const txBytesPerSecond = ((currentRxBytes - prevRxBytes) / elapsedMs) * 1000;
                    this.setRateMetrics(txBytesPerSecond, rxBytesPerSecond);
                } else {
                    this.setRateMetrics(
                        ((payload.request_frame_bytes ?? this.lastPayloadBytes) / Math.max(latencyMs, 1)) * 1000,
                        ((payload.ack_frame_bytes ?? downloadBytes) / Math.max(latencyMs, 1)) * 1000
                    );
                }
                this.previousServerReceivedAt = currentAt;
                this.previousServerTxBytes = currentTxBytes;
                this.previousServerRxBytes = currentRxBytes;
                this.updateMetrics(latencyMs, downloadBytes, false);
                this.updateTotals();
            } else {
                this.totalReceivedPackets += 1;
                this.totalReceivedBytes += downloadBytes;
                this.updateMetrics(latencyMs, downloadBytes);
            }
            this.pulseDirection("rx", this.config.labels?.rx ?? "RX");
            this.spawnPulse("rx");
        });

        this.on("close", () => {
            this.stopLoop();
            this.setConnection("disconnected", "Disconnected");
        });

        this.on("error", () => {
            this.stopLoop();
            this.setConnection("disconnected", "Error");
        });
    }

    bind() {
        if (this.toggleButton) {
            this.toggleButton.addEventListener("click", () => this.toggleLoop());
        }
        if (this.tempoInput) {
            this.tempoInput.addEventListener("input", () => {
                this.updateTempoLabel();
                if (this.periodic.isRunning()) {
                    this.periodic.start(Infinity, this.getTempoMs());
                }
            });
        }
        if (this.payloadInput) {
            this.payloadInput.addEventListener("input", () => this.updatePayloadLabel());
        }
        this.initPayloadWorker();
        this.updateTempoLabel();
        this.updatePayloadLabel();
        this.updateTotals();
        this.connectChannel();
        this.initThree();
    }
}

export function attachHeartbeatMonitors(config: HeartbeatMonitorConfig) {
    document.querySelectorAll<HTMLElement>(config.selector).forEach((element) => {
        new HeartbeatMonitorComponent(element, config);
    });
}


