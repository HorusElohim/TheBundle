import { WebSocketWidget, createPeriodicSender } from "../headless/ws.js";

class HeartbeatWidget extends WebSocketWidget {
    constructor(element) {
        super(element, { reconnectDelayMs: 1500 });
        this.element = element;
        this.status = element.querySelector('[data-role="status"]');
        this.tempoInput = element.querySelector('[data-control="tempo"]');
        this.tempoValue = element.querySelector('[data-control-value="tempo"]');
        this.toggleButton = element.querySelector('[data-action="toggle"]');
        this.periodic = createPeriodicSender(() => this.sendHeartbeat());
        this.bind();
    }

    setState(state, label) {
        this.element.dataset.state = state;
        if (this.status) {
            this.status.textContent = label;
        }
        if (this.toggleButton) {
            this.toggleButton.textContent = state === "active" ? "Stop" : "Start";
        }
    }

    getTempoMs() {
        const tempoSeconds = Number.parseFloat(this.tempoInput?.value || "1.0");
        return Math.max(100, Math.round(tempoSeconds * 1000));
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
        const sentAt = Date.now();
        const payload = { type: "keepalive", sent_at: sentAt };
        this.send(payload);
        return true;
    }

    toggle() {
        if (this.periodic.isRunning()) {
            this.periodic.stop();
            this.setState("idle", "Idle");
            return;
        }
        const cadenceMs = this.getTempoMs();
        this.periodic.start(Infinity, cadenceMs);
        this.setState("active", "Active");
    }

    bind() {
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
        this.updateTempoLabel();
        this.connectChannel();
    }

    connectChannel() {
        this.channel = this.connect();
        if (!this.channel) {
            return;
        }

        this.on("connecting", () => this.setState("connecting", "Connecting"));
        this.on("open", () => this.setState("idle", "Idle"));
        this.on("close", () => {
            this.periodic.stop();
            this.setState("idle", "Disconnected");
        });
        this.on("error", () => {
            this.periodic.stop();
            this.setState("idle", "Error");
        });
    }
}

document.querySelectorAll('[data-widget="ws-heartbeat"]').forEach((element) => {
    new HeartbeatWidget(element);
});
