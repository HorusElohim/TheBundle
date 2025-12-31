import { WebSocketWidget, createPeriodicSender } from "../headless/ws.js";

class EccWidget extends WebSocketWidget {
    constructor(element) {
        super(element, { reconnectDelayMs: 1500 });
        this.element = element;
        this.connectionPill = element.querySelector('[data-role="connection"]');
        this.directionPill = element.querySelector('[data-role="direction"]');
        this.latencyMetric = element.querySelector('[data-metric="latency"]');
        this.uploadMetric = element.querySelector('[data-metric="upload"]');
        this.downloadMetric = element.querySelector('[data-metric="download"]');
        this.toggleButton = element.querySelector('[data-action="toggle"]');
        this.toggleLabel = element.querySelector('[data-role="toggle-label"]');
        this.tempoInput = element.querySelector('[data-control="tempo"]');
        this.tempoValue = element.querySelector('[data-control-value="tempo"]');
        this.timelineScroll = element.querySelector('[data-role="timeline-scroll"]');
        this.timeline = element.querySelector('[data-role="timeline"]');
        this.timelineStartLabel = element.querySelector('[data-role="timeline-start"]');
        this.timelineEndLabel = element.querySelector('[data-role="timeline-end"]');
        this.ackTimeoutMs = 3000;
        this.pxPerMs = 0.06;
        this.encoder = new TextEncoder();
        this.connected = false;
        this.pending = false;
        this.pendingTimer = null;
        this.idleTimer = null;
        this.lastSentAt = null;
        this.lastUploadBytes = 0;
        this.timelineStartAt = null;
        this.timelineEndOffset = 0;
        this.autoScroll = true;
        this.periodic = createPeriodicSender(() => this.sendKeepalive());
        this.bind();
    }

    clamp(value, min, max) {
        return Math.min(max, Math.max(min, value));
    }

    formatMetric(value, suffix) {
        return `${value.toFixed(1)} ${suffix}`;
    }

    bytesToKbps(bytes, ms) {
        return (bytes / Math.max(ms, 1)) * 1000 / 1024;
    }

    beatHeightForBytes(bytes) {
        const min = 24;
        const max = 120;
        const scaled = min + Math.sqrt(Math.max(bytes, 1)) * 6;
        return this.clamp(scaled, min, max);
    }

    updateTimelineLabels() {
        const elapsedMs = this.timelineEndOffset / this.pxPerMs;
        const elapsedSeconds = elapsedMs > 0 ? (elapsedMs / 1000).toFixed(1) : "0.0";
        if (this.timelineStartLabel) {
            this.timelineStartLabel.textContent = "0.0s";
        }
        if (this.timelineEndLabel) {
            this.timelineEndLabel.textContent = `${elapsedSeconds}s`;
        }
    }

    updateSliderValues() {
        if (this.tempoInput && this.tempoValue) {
            const tempoSeconds = Number.parseFloat(this.tempoInput.value || "0.1");
            const tempoMs = Math.round(tempoSeconds * 1000);
            this.tempoValue.textContent = `${tempoSeconds.toFixed(1)}s (${tempoMs}ms)`;
        }
    }

    getTempoMs() {
        const tempoSeconds = Number.parseFloat(this.tempoInput?.value || "0.1");
        const tempoMs = Number.isFinite(tempoSeconds) ? tempoSeconds * 1000 : 100;
        return this.clamp(Math.round(tempoMs), 50, 10000);
    }

    setDirection(direction, label) {
        this.element.dataset.direction = direction;
        if (this.directionPill) {
            this.directionPill.textContent = label || (direction === "tx" ? "TX" : direction === "rx" ? "RX" : "Idle");
        }
    }

    setConnection(state) {
        this.element.dataset.connection = state;
        this.connected = state === "connected";
        if (this.connectionPill) {
            this.connectionPill.textContent =
                state === "connected" ? "Connected" : state === "connecting" ? "Connecting" : "Disconnected";
        }
        if (this.toggleButton) {
            this.toggleButton.disabled = !this.connected;
        }
        if (!this.connected) {
            this.setDirection("idle");
        }
    }

    pulse(direction) {
        this.element.dataset.direction = direction;
        clearTimeout(this.idleTimer);
        this.idleTimer = setTimeout(() => {
            this.setDirection("idle");
        }, 900);
    }

    isNearTimelineEnd() {
        if (!this.timelineScroll) {
            return true;
        }
        return this.timelineScroll.scrollLeft + this.timelineScroll.clientWidth >= this.timelineScroll.scrollWidth - 40;
    }

    shiftTimeline(shiftPx) {
        if (!this.timeline) {
            return;
        }
        const beats = this.timeline.querySelectorAll(".ws-ecc__beat");
        beats.forEach((beat) => {
            const currentLeft = Number.parseFloat(beat.style.left || "0");
            beat.style.left = `${currentLeft + shiftPx}px`;
        });
    }

    addBeat(direction, timestamp, sizeBytes) {
        if (!this.timeline) {
            return;
        }
        if (this.timelineStartAt === null) {
            this.timelineStartAt = timestamp;
        } else if (timestamp < this.timelineStartAt) {
            const shiftMs = this.timelineStartAt - timestamp;
            const shiftPx = Math.round(shiftMs * this.pxPerMs);
            if (shiftPx > 0) {
                this.shiftTimeline(shiftPx);
                this.timelineEndOffset += shiftPx;
                if (this.timelineScroll && this.autoScroll) {
                    this.timelineScroll.scrollLeft += shiftPx;
                }
            }
            this.timelineStartAt = timestamp;
        }
        const offset = Math.max(0, Math.round((timestamp - this.timelineStartAt) * this.pxPerMs));
        this.timelineEndOffset = Math.max(this.timelineEndOffset, offset);
        const beat = document.createElement("span");
        beat.className = `ws-ecc__beat ws-ecc__beat--${direction}`;
        beat.style.left = `${offset}px`;
        const beatBytes = Number.isFinite(sizeBytes) ? sizeBytes : direction === "tx" ? this.lastUploadBytes : 0;
        if (beatBytes) {
            beat.style.height = `${this.beatHeightForBytes(beatBytes)}px`;
        }
        this.timeline.appendChild(beat);
        beat.classList.add("is-fresh");
        beat.addEventListener(
            "animationend",
            () => {
                beat.classList.remove("is-fresh");
            },
            { once: true }
        );

        if (this.timelineScroll) {
            const minWidth = Math.max(this.timelineEndOffset + 120, this.timelineScroll.clientWidth);
            this.timeline.style.width = `${minWidth}px`;
            if (this.autoScroll) {
                this.timelineScroll.scrollLeft = this.timelineScroll.scrollWidth;
            }
        }

        this.updateTimelineLabels();
    }

    sendKeepalive() {
        if (!this.channel || !this.isOpen() || this.pending) {
            return false;
        }
        this.pending = true;

        const sentAt = Date.now();
        this.lastSentAt = sentAt;
        const payload = { type: "keepalive", sent_at: sentAt };
        const payloadText = JSON.stringify(payload);
        this.lastUploadBytes = this.encoder.encode(payloadText).length;

        this.send(payloadText);
        this.setDirection("tx", "TX");
        this.pulse("tx");
        this.addBeat("tx", sentAt);

        clearTimeout(this.pendingTimer);
        this.pendingTimer = window.setTimeout(() => {
            this.pending = false;
            this.setDirection("idle", "Timeout");
        }, this.ackTimeoutMs);

        return true;
    }

    stopLoop() {
        this.periodic.stop();
        this.pending = false;
        clearTimeout(this.pendingTimer);
        this.updateToggleLabel();
        this.setDirection("idle");
    }

    startLoop() {
        if (!this.connected) {
            return;
        }
        this.periodic.start(Infinity, this.getTempoMs());
        this.updateToggleLabel();
    }

    toggleLoop() {
        if (this.periodic.isRunning()) {
            this.stopLoop();
            return;
        }
        this.startLoop();
    }

    updateToggleLabel() {
        if (!this.toggleLabel) {
            return;
        }
        this.toggleLabel.textContent = this.periodic.isRunning() ? "Stop" : "Start";
    }

    bind() {
        if (this.toggleButton) {
            this.toggleButton.addEventListener("click", () => this.toggleLoop());
        }

        if (this.tempoInput) {
            this.tempoInput.addEventListener("input", () => {
                this.updateSliderValues();
                if (this.periodic.isRunning()) {
                    this.periodic.start(Infinity, this.getTempoMs());
                }
            });
        }

        if (this.timelineScroll) {
            this.timelineScroll.addEventListener(
                "scroll",
                () => {
                    this.autoScroll = this.isNearTimelineEnd();
                },
                { passive: true }
            );
        }

        this.updateSliderValues();
        this.updateToggleLabel();
        this.connectChannel();
    }

    connectChannel() {
        this.channel = this.connect();
        if (!this.channel) {
            return;
        }

        this.on("connecting", () => {
            this.setConnection("connecting");
        });

        this.on("open", () => {
            this.setConnection("connected");
        });

        this.on("message", (event) => {
            const payload = event.detail?.data;
            if (!payload || payload?.type !== "keepalive_ack") {
                return;
            }
            const sentAt = payload.sent_at;
            if (!sentAt || !this.pending || sentAt !== this.lastSentAt) {
                return;
            }
            this.pending = false;
            clearTimeout(this.pendingTimer);

            const now = Date.now();
            const latencyMs = now - sentAt;
            const downloadBytes = this.encoder.encode(event.detail?.raw || "").length;
            const uploadKbps = this.bytesToKbps(this.lastUploadBytes, latencyMs);
            const downloadKbps = this.bytesToKbps(downloadBytes, latencyMs);

            if (this.latencyMetric) {
                this.latencyMetric.textContent = `${Math.round(latencyMs)} ms`;
            }
            if (this.uploadMetric) {
                this.uploadMetric.textContent = this.formatMetric(uploadKbps, "kb/s");
            }
            if (this.downloadMetric) {
                this.downloadMetric.textContent = this.formatMetric(downloadKbps, "kb/s");
            }

            this.setDirection("rx");
            this.pulse("rx");
            this.addBeat("rx", payload.received_at || now, downloadBytes);
        });

        this.on("close", () => {
            this.stopLoop();
            this.setConnection("disconnected");
        });

        this.on("error", () => {
            this.stopLoop();
            this.setConnection("disconnected");
        });
    }
}

document.querySelectorAll('[data-widget="ws-ecc"]').forEach((element) => {
    new EccWidget(element);
});
