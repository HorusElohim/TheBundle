import { WebSocketComponent, createPeriodicSender } from "../../base/frontend/ws.js";

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const lerp = (a, b, t) => a + (b - a) * t;

class HeartbeatCardioComponent extends WebSocketComponent {
    constructor(element) {
        super(element, { reconnectDelayMs: 1500 });
        this.status = element.querySelector('[data-role="connection"]');
        this.direction = element.querySelector('[data-role="direction"]');
        this.toggleButton = element.querySelector('[data-action="toggle"]');
        this.toggleLabel = element.querySelector('[data-role="toggle-label"]');
        this.tempoInput = element.querySelector('[data-control="tempo"]');
        this.tempoValue = element.querySelector('[data-control-value="tempo"]');

        this.latencyMetric = element.querySelector('[data-metric="latency"]');
        this.jitterMetric = element.querySelector('[data-metric="jitter"]');
        this.rxMetric = element.querySelector('[data-metric="rx-rate"]');
        this.totalReceivedMetric = element.querySelector('[data-metric="total-received"]');

        this.canvas = element.querySelector('[data-role="canvas"]');
        this.ctx = this.canvas ? this.canvas.getContext("2d") : null;
        this.periodic = createPeriodicSender(() => this.sendHeartbeat());
        this.samples = Array.from({ length: 160 }, () => 0);
        this.lastSentAt = 0;
        this.lastLatency = null;
        this.lastAckAt = 0;
        this.rxBytes = 0;
        this.rxPackets = 0;
        this.pulse = 0;
        this.phase = 0;
        this.animationFrame = 0;
        this.lastFrameAt = 0;
        this.bind();
    }

    bind() {
        this.connectChannel();
        this.updateTempoLabel();
        this.resizeCanvas();
        window.addEventListener("resize", () => this.resizeCanvas());
        if (this.toggleButton) {
            this.toggleButton.addEventListener("click", () => this.toggle());
        }
        if (this.tempoInput) {
            this.tempoInput.addEventListener("input", () => {
                this.updateTempoLabel();
                if (this.periodic.isRunning()) {
                    this.periodic.start(Infinity, this.getTempoMs());
                }
            });
        }
        this.animationFrame = requestAnimationFrame((now) => this.render(now));
    }

    connectChannel() {
        this.channel = this.connect();
        if (!this.channel) {
            return;
        }
        this.on("connecting", () => this.setConnection("connecting", "Connecting"));
        this.on("open", () => {
            this.setConnection("connected", "Connected");
            if (this.toggleButton) {
                this.toggleButton.disabled = false;
            }
        });
        this.on("close", () => {
            this.periodic.stop();
            this.setConnection("disconnected", "Disconnected");
            this.setDirection("idle", "Idle");
            if (this.toggleButton) {
                this.toggleButton.disabled = true;
            }
            this.setRunning(false);
        });
        this.on("error", () => {
            this.periodic.stop();
            this.setConnection("error", "Error");
            this.setDirection("idle", "Idle");
            this.setRunning(false);
        });
        this.on("message", (event) => this.onMessage(event.detail.data));
    }

    setConnection(state, label) {
        this.element.dataset.state = state;
        if (this.status) {
            this.status.textContent = label;
        }
    }

    setDirection(direction, label) {
        this.element.dataset.direction = direction;
        if (this.direction) {
            this.direction.textContent = label;
        }
    }

    setRunning(running) {
        if (!this.toggleLabel) {
            return;
        }
        this.toggleLabel.textContent = running ? "Stop Cardio" : "Start Cardio";
    }

    getTempoMs() {
        const tempoSeconds = Number.parseFloat(this.tempoInput?.value || "1.0");
        return Math.max(150, Math.round(tempoSeconds * 1000));
    }

    updateTempoLabel() {
        if (!this.tempoValue) {
            return;
        }
        const tempoSeconds = Number.parseFloat(this.tempoInput?.value || "1.0");
        this.tempoValue.textContent = `${tempoSeconds.toFixed(1)}s`;
    }

    sendHeartbeat() {
        if (!this.channel || !this.isOpen()) {
            return false;
        }
        this.lastSentAt = Date.now();
        this.pulse = 1;
        this.setDirection("tx", "TX");
        this.send({ type: "keepalive", sent_at: this.lastSentAt });
        return true;
    }

    toggle() {
        if (this.periodic.isRunning()) {
            this.periodic.stop();
            this.setRunning(false);
            this.setDirection("idle", "Idle");
            return;
        }
        this.periodic.start(Infinity, this.getTempoMs());
        this.setRunning(true);
    }

    onMessage(payload) {
        if (!payload || payload.type !== "keepalive_ack") {
            return;
        }
        this.setDirection("rx", "RX");
        const now = Date.now();
        const latency = Math.max(1, now - (payload.sent_at || this.lastSentAt || now));
        const jitter = this.lastLatency == null ? 0 : Math.abs(latency - this.lastLatency);
        this.lastLatency = latency;

        if (this.latencyMetric) {
            this.latencyMetric.textContent = `${Math.round(latency)} ms`;
        }
        if (this.jitterMetric) {
            this.jitterMetric.textContent = `${Math.round(jitter)} ms`;
        }

        const ackSize = typeof payload.ack_frame_bytes === "number" ? payload.ack_frame_bytes : 0;
        if (typeof payload.server_tx_packets === "number") {
            this.rxPackets = payload.server_tx_packets;
        } else {
            this.rxPackets += 1;
        }
        if (typeof payload.server_tx_bytes === "number") {
            this.rxBytes = payload.server_tx_bytes;
        } else {
            this.rxBytes += ackSize;
        }

        const elapsed = Math.max(1, now - (this.lastAckAt || now - latency));
        this.lastAckAt = now;
        const rxRate = (Math.max(ackSize, 1) / elapsed) * 1000;
        if (this.rxMetric) {
            this.rxMetric.textContent = `RX: ${this.formatRate(rxRate)}`;
        }
        if (this.totalReceivedMetric) {
            this.totalReceivedMetric.textContent = `${this.formatBytes(this.rxBytes)} (${this.rxPackets} pkgs)`;
        }
    }

    formatRate(bytesPerSecond) {
        if (bytesPerSecond < 1024) return `${bytesPerSecond.toFixed(0)} B/s`;
        if (bytesPerSecond < 1024 * 1024) return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
        return `${(bytesPerSecond / (1024 * 1024)).toFixed(2)} MB/s`;
    }

    formatBytes(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    resizeCanvas() {
        if (!this.canvas || !this.ctx) {
            return;
        }
        const bounds = this.canvas.getBoundingClientRect();
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        this.canvas.width = Math.max(1, Math.floor(bounds.width * dpr));
        this.canvas.height = Math.max(1, Math.floor(bounds.height * dpr));
        this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    updateWave(dt) {
        if (!this.periodic.isRunning()) {
            this.pulse = 0;
            const previous = this.samples[this.samples.length - 1] || 0;
            const next = lerp(previous, 0, 0.18);
            this.samples.push(Math.abs(next) < 0.0005 ? 0 : next);
            this.samples.shift();
            return;
        }

        const tempoMs = this.getTempoMs();
        const hz = 1000 / Math.max(tempoMs, 1);
        this.phase += dt * hz;
        this.pulse *= Math.pow(0.12, dt);

        const cycle = this.phase % 1;
        const p = this.pulse;
        let value = 0.02 * Math.sin(this.phase * Math.PI * 6);
        if (cycle > 0.18 && cycle < 0.22) value += -0.18 * p;
        if (cycle > 0.24 && cycle < 0.27) value += 0.95 * p;
        if (cycle > 0.27 && cycle < 0.31) value += -0.32 * p;
        if (cycle > 0.52 && cycle < 0.62) value += 0.28 * p;

        const smooth = lerp(this.samples[this.samples.length - 1] || 0, value, 0.55);
        this.samples.push(smooth);
        this.samples.shift();
    }

    render(now) {
        if (!this.ctx || !this.canvas) {
            return;
        }
        if (!this.lastFrameAt) {
            this.lastFrameAt = now;
        }
        const dt = Math.min((now - this.lastFrameAt) / 1000, 0.05);
        this.lastFrameAt = now;
        this.updateWave(dt);

        const ctx = this.ctx;
        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;
        const horizon = height * 0.6;
        const baseY = height * 0.42;

        const bg = ctx.createLinearGradient(0, 0, 0, height);
        bg.addColorStop(0, "#03182d");
        bg.addColorStop(1, "#01060f");
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, width, height);

        ctx.strokeStyle = "rgba(54, 162, 235, 0.18)";
        ctx.lineWidth = 1;
        for (let i = 0; i <= 10; i += 1) {
            const y = horizon + (i / 10) * (height - horizon);
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
        for (let i = -8; i <= 8; i += 1) {
            const x = width * 0.5 + i * 42;
            ctx.beginPath();
            ctx.moveTo(x, horizon);
            ctx.lineTo(width * 0.5 + i * 130, height);
            ctx.stroke();
        }

        for (let depth = 0; depth < 6; depth += 1) {
            const t = depth / 5;
            const zScale = 1 - t * 0.45;
            const yOffset = t * 62;
            ctx.beginPath();
            for (let i = 0; i < this.samples.length; i += 1) {
                const n = i / (this.samples.length - 1);
                const x = n * width;
                const y = baseY + yOffset - this.samples[i] * 80 * zScale;
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }
            const alpha = 0.11 + (1 - t) * 0.24;
            ctx.strokeStyle = `rgba(34, 197, 94, ${alpha})`;
            ctx.lineWidth = 1.2 + (1 - t) * 1.1;
            ctx.stroke();
        }

        ctx.beginPath();
        for (let i = 0; i < this.samples.length; i += 1) {
            const n = i / (this.samples.length - 1);
            const x = n * width;
            const y = baseY - this.samples[i] * 92;
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        const glow = ctx.createLinearGradient(0, 0, width, 0);
        glow.addColorStop(0, "rgba(0, 230, 255, 0.35)");
        glow.addColorStop(0.5, "rgba(34, 197, 94, 0.95)");
        glow.addColorStop(1, "rgba(249, 115, 22, 0.6)");
        ctx.strokeStyle = glow;
        ctx.lineWidth = 2.6;
        ctx.stroke();

        const latest = this.samples[this.samples.length - 1];
        const orbX = width * 0.94;
        const orbY = baseY - latest * 92;
        const orb = ctx.createRadialGradient(orbX, orbY, 0, orbX, orbY, 16);
        orb.addColorStop(0, "rgba(255, 255, 255, 0.95)");
        orb.addColorStop(1, "rgba(34, 197, 94, 0)");
        ctx.fillStyle = orb;
        ctx.beginPath();
        ctx.arc(orbX, orbY, 16, 0, Math.PI * 2);
        ctx.fill();

        this.animationFrame = requestAnimationFrame((ts) => this.render(ts));
    }
}

document.querySelectorAll('[data-component="ws-heartbeat-cardio"]').forEach((element) => {
    new HeartbeatCardioComponent(element);
});
