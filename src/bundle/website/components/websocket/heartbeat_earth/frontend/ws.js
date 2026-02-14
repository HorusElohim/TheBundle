import { WebSocketComponent, createPeriodicSender } from "../../base/frontend/ws.js";

const THREE_MODULE_URL = "https://unpkg.com/three@0.161.0/build/three.module.js";

class HeartBeatMonitorEarthComponent extends WebSocketComponent {
    constructor(element) {
        super(element, { reconnectDelayMs: 1500 });
        this.element = element;
        this.connectionBadge = element.querySelector('[data-role="connection"]');
        this.directionBadge = element.querySelector('[data-role="direction"]');
        this.toggleButton = element.querySelector('[data-action="toggle"]');
        this.toggleLabel = element.querySelector('[data-role="toggle-label"]');
        this.tempoInput = element.querySelector('[data-control="tempo"]');
        this.tempoValue = element.querySelector('[data-control-value="tempo"]');
        this.canvas = element.querySelector('[data-role="canvas"]');
        this.latencyMetric = element.querySelector('[data-metric="latency"]');
        this.jitterMetric = element.querySelector('[data-metric="jitter"]');
        this.throughputMetric = element.querySelector('[data-metric="throughput"]');
        this.totalSentMetric = element.querySelector('[data-metric="total-sent"]');
        this.totalReceivedMetric = element.querySelector('[data-metric="total-received"]');

        this.encoder = new TextEncoder();
        this.pending = false;
        this.lastSentAt = null;
        this.lastPayloadBytes = 0;
        this.previousLatency = null;
        this.totalSentPackets = 0;
        this.totalReceivedPackets = 0;
        this.totalSentBytes = 0;
        this.totalReceivedBytes = 0;
        this.idleTimer = null;
        this.periodic = createPeriodicSender(() => this.sendKeepalive());

        this.three = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.earthGroup = null;
        this.effects = [];
        this.nodeVectors = null;
        this.animationFrame = null;
        this.resizeObserver = null;

        this.bind();
    }

    setConnection(state, label) {
        this.element.dataset.state = state;
        if (this.connectionBadge) {
            this.connectionBadge.textContent = label;
        }
        if (this.toggleButton) {
            this.toggleButton.disabled = state !== "connected";
        }
    }

    setDirection(direction, label) {
        this.element.dataset.direction = direction;
        if (this.directionBadge) {
            this.directionBadge.textContent = label;
        }
    }

    pulseDirection(direction, label) {
        this.setDirection(direction, label);
        window.clearTimeout(this.idleTimer);
        this.idleTimer = window.setTimeout(() => this.setDirection("idle", "Idle"), 850);
    }

    updateTempoLabel() {
        if (!this.tempoValue) {
            return;
        }
        const seconds = Number.parseFloat(this.tempoInput?.value || "1");
        this.tempoValue.textContent = `${seconds.toFixed(1)}s`;
    }

    getTempoMs() {
        const seconds = Number.parseFloat(this.tempoInput?.value || "1");
        return Math.max(200, Math.round(seconds * 1000));
    }

    formatKbps(bytes, elapsedMs) {
        const kbps = (bytes / Math.max(elapsedMs, 1)) * 1000 / 1024;
        return kbps.toFixed(1);
    }

    formatBytes(bytes) {
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

    emitToast(body, level = "info") {
        window.dispatchEvent(
            new CustomEvent("bundle:toast", {
                detail: {
                    source: "heartbeat-earth",
                    body,
                    level,
                    timestamp: Date.now(),
                },
            })
        );
    }

    updateTotals() {
        if (this.totalSentMetric) {
            this.totalSentMetric.textContent = `${this.formatBytes(this.totalSentBytes)} (${this.totalSentPackets} pkgs)`;
        }
        if (this.totalReceivedMetric) {
            this.totalReceivedMetric.textContent = `${this.formatBytes(this.totalReceivedBytes)} (${this.totalReceivedPackets} pkgs)`;
        }
    }

    updateMetrics(latencyMs, downloadBytes) {
        const jitter = this.previousLatency == null ? 0 : Math.abs(latencyMs - this.previousLatency);
        this.previousLatency = latencyMs;

        if (this.latencyMetric) {
            this.latencyMetric.textContent = `${Math.round(latencyMs)} ms`;
        }
        if (this.jitterMetric) {
            this.jitterMetric.textContent = `${Math.round(jitter)} ms`;
        }
        if (this.throughputMetric) {
            const tx = this.formatKbps(this.lastPayloadBytes, latencyMs);
            const rx = this.formatKbps(downloadBytes, latencyMs);
            this.throughputMetric.textContent = `${tx} / ${rx} kb/s`;
        }
        this.updateTotals();
    }

    sendKeepalive() {
        if (!this.channel || !this.isOpen() || this.pending) {
            return false;
        }
        const sentAt = Date.now();
        const payload = { type: "keepalive", sent_at: sentAt };
        const raw = JSON.stringify(payload);
        this.lastSentAt = sentAt;
        this.lastPayloadBytes = this.encoder.encode(raw).length;
        this.totalSentPackets += 1;
        this.totalSentBytes += this.lastPayloadBytes;
        this.updateTotals();
        this.pending = true;
        this.send(raw);
        this.pulseDirection("tx", "TX");
        this.spawnPulse("tx");

        window.setTimeout(() => {
            if (!this.pending) {
                return;
            }
            this.pending = false;
            this.setDirection("idle", "Timeout");
            this.emitToast("Heartbeat timeout from Earth monitor.", "warning");
        }, 3200);
        return true;
    }

    stopLoop() {
        this.pending = false;
        this.periodic.stop();
        if (this.toggleLabel) {
            this.toggleLabel.textContent = "Start Sweep";
        }
    }

    startLoop() {
        if (!this.isOpen()) {
            return;
        }
        this.periodic.start(Infinity, this.getTempoMs());
        if (this.toggleLabel) {
            this.toggleLabel.textContent = "Stop Sweep";
        }
    }

    toggleLoop() {
        if (this.periodic.isRunning()) {
            this.stopLoop();
            return;
        }
        this.startLoop();
    }

    latLonToVector3(lat, lon, radius) {
        const phi = (90 - lat) * (Math.PI / 180);
        const theta = (lon + 180) * (Math.PI / 180);
        const x = -(radius * Math.sin(phi) * Math.cos(theta));
        const z = radius * Math.sin(phi) * Math.sin(theta);
        const y = radius * Math.cos(phi);
        return new this.three.Vector3(x, y, z);
    }

    spawnNode(position, color) {
        const geometry = new this.three.SphereGeometry(0.035, 16, 16);
        const material = new this.three.MeshBasicMaterial({ color });
        const marker = new this.three.Mesh(geometry, material);
        marker.position.copy(position);
        this.earthGroup.add(marker);
    }

    spawnRing(position, color) {
        const geometry = new this.three.RingGeometry(0.02, 0.05, 30);
        const material = new this.three.MeshBasicMaterial({
            color,
            transparent: true,
            opacity: 0.7,
            side: this.three.DoubleSide,
        });
        const ring = new this.three.Mesh(geometry, material);
        const normal = position.clone().normalize();
        ring.quaternion.setFromUnitVectors(new this.three.Vector3(0, 0, 1), normal);
        ring.position.copy(position);
        ring.userData = { born: performance.now(), ttl: 900, kind: "ring" };
        this.effects.push(ring);
        this.earthGroup.add(ring);
    }

    spawnPulse(direction) {
        if (!this.three || !this.earthGroup || !this.nodeVectors) {
            return;
        }
        const tx = direction === "tx";
        const start = tx ? this.nodeVectors.client : this.nodeVectors.server;
        const end = tx ? this.nodeVectors.server : this.nodeVectors.client;
        const color = tx ? 0x4ade80 : 0xfb923c;

        const midpoint = start
            .clone()
            .add(end)
            .multiplyScalar(0.5)
            .normalize()
            .multiplyScalar(1.48);
        const curve = new this.three.QuadraticBezierCurve3(start.clone(), midpoint, end.clone());
        const points = curve.getPoints(40);
        const geometry = new this.three.BufferGeometry().setFromPoints(points);
        const material = new this.three.LineBasicMaterial({ color, transparent: true, opacity: 0.95 });
        const line = new this.three.Line(geometry, material);
        line.userData = { born: performance.now(), ttl: 1100, kind: "line" };
        this.effects.push(line);
        this.earthGroup.add(line);

        this.spawnRing(end.clone().multiplyScalar(1.012), color);
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

    async initThree() {
        if (!this.canvas || this.renderer) {
            return;
        }
        try {
            const module = await import(THREE_MODULE_URL);
            this.three = module;
        } catch (error) {
            this.setConnection("disconnected", "3D Unavailable");
            return;
        }

        const THREE = this.three;
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
        this.camera.position.set(0, 0, 3.5);

        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true,
        });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.resizeRenderer();

        const ambient = new THREE.AmbientLight(0x8fdfff, 0.55);
        const rimLight = new THREE.DirectionalLight(0x66e5ff, 0.65);
        rimLight.position.set(2.2, 1.2, 2);
        const fillLight = new THREE.DirectionalLight(0x3b82f6, 0.5);
        fillLight.position.set(-2, -1.4, -1.4);
        this.scene.add(ambient, rimLight, fillLight);

        this.earthGroup = new THREE.Group();
        this.scene.add(this.earthGroup);

        const earthGeometry = new THREE.SphereGeometry(1, 64, 64);
        const earthMaterial = new THREE.MeshStandardMaterial({
            color: 0x12345f,
            emissive: 0x0a1b34,
            metalness: 0.28,
            roughness: 0.56,
        });
        const earth = new THREE.Mesh(earthGeometry, earthMaterial);
        this.earthGroup.add(earth);

        const wireframe = new THREE.LineSegments(
            new THREE.WireframeGeometry(new THREE.SphereGeometry(1.02, 28, 28)),
            new THREE.LineBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.18 })
        );
        this.earthGroup.add(wireframe);

        const atmosphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.08, 40, 40),
            new THREE.MeshBasicMaterial({
                color: 0x7dd3fc,
                transparent: true,
                opacity: 0.09,
                side: THREE.BackSide,
            })
        );
        this.earthGroup.add(atmosphere);

        const client = this.latLonToVector3(37.7749, -122.4194, 1.03);
        const server = this.latLonToVector3(64.1466, -21.9426, 1.03);
        this.nodeVectors = { client, server };
        this.spawnNode(client, 0x4ade80);
        this.spawnNode(server, 0xfb923c);

        this.resizeObserver = new ResizeObserver(() => this.resizeRenderer());
        this.resizeObserver.observe(this.canvas);
        this.animate();
    }

    animate() {
        if (!this.renderer || !this.scene || !this.camera || !this.earthGroup || !this.three) {
            return;
        }
        const now = performance.now();
        this.earthGroup.rotation.y += 0.0024;

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
            if (item.userData.kind === "ring") {
                const scale = 1 + progress * 5;
                item.scale.setScalar(scale);
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
        });

        this.on("message", (event) => {
            const payload = event.detail?.data;
            if (!payload || payload.type !== "keepalive_ack" || !this.pending) {
                return;
            }
            if (payload.sent_at !== this.lastSentAt) {
                return;
            }
            this.pending = false;
            const now = Date.now();
            const latencyMs = Math.max(1, now - payload.sent_at);
            const downloadBytes = this.encoder.encode(event.detail?.raw || "").length;
            this.totalReceivedPackets += 1;
            this.totalReceivedBytes += downloadBytes;
            this.updateMetrics(latencyMs, downloadBytes);
            this.pulseDirection("rx", "RX");
            this.spawnPulse("rx");
            this.emitToast(`Earth heartbeat ack in ${Math.round(latencyMs)} ms.`, "success");
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
        this.updateTempoLabel();
        this.updateTotals();
        this.connectChannel();
        this.initThree();
    }
}

document.querySelectorAll('[data-component="ws-heartbeat-earth"]').forEach((element) => {
    new HeartBeatMonitorEarthComponent(element);
});
