export class SphericalCameraRig {
    camera;
    radius;
    azimuth;
    polar;
    minRadius;
    maxRadius;
    rotateSpeed;
    zoomSpeed;
    minPolar;
    maxPolar;
    dragging;
    lastX;
    lastY;
    canvas;
    cleanup;
    constructor(camera, options) {
        this.camera = camera;
        this.radius = options.radius;
        this.azimuth = options.azimuth ?? 0;
        this.polar = options.polar ?? Math.PI / 2;
        this.minRadius = options.minRadius ?? 1;
        this.maxRadius = options.maxRadius ?? 100;
        this.rotateSpeed = options.rotateSpeed ?? 0.01;
        this.zoomSpeed = options.zoomSpeed ?? 0.003;
        this.minPolar = options.minPolar ?? 0.12;
        this.maxPolar = options.maxPolar ?? Math.PI - 0.12;
        this.dragging = false;
        this.lastX = 0;
        this.lastY = 0;
        this.canvas = null;
        this.cleanup = [];
        this.update();
    }
    setRadiusLimits(minRadius, maxRadius) {
        this.minRadius = minRadius;
        this.maxRadius = maxRadius;
        this.radius = Math.min(this.maxRadius, Math.max(this.minRadius, this.radius));
        this.update();
    }
    update() {
        if (!this.camera) {
            return;
        }
        const sinPolar = Math.sin(this.polar);
        const x = this.radius * sinPolar * Math.cos(this.azimuth);
        const y = this.radius * Math.cos(this.polar);
        const z = this.radius * sinPolar * Math.sin(this.azimuth);
        this.camera.position.set(x, y, z);
        this.camera.lookAt(0, 0, 0);
    }
    bind(canvas) {
        this.canvas = canvas;
        canvas.style.touchAction = "none";
        const onPointerDown = (event) => {
            this.dragging = true;
            this.lastX = event.clientX;
            this.lastY = event.clientY;
            canvas.setPointerCapture(event.pointerId);
        };
        const onPointerMove = (event) => {
            if (!this.dragging) {
                return;
            }
            const dx = event.clientX - this.lastX;
            const dy = event.clientY - this.lastY;
            this.lastX = event.clientX;
            this.lastY = event.clientY;
            this.azimuth -= dx * this.rotateSpeed;
            this.polar = Math.min(this.maxPolar, Math.max(this.minPolar, this.polar + dy * this.rotateSpeed));
            this.update();
        };
        const stopDrag = (pointerId) => {
            this.dragging = false;
            if (pointerId != null) {
                canvas.releasePointerCapture(pointerId);
            }
        };
        const onPointerUp = (event) => stopDrag(event.pointerId);
        const onPointerCancel = (event) => stopDrag(event.pointerId);
        const onPointerLeave = () => stopDrag();
        const onWheel = (event) => {
            event.preventDefault();
            this.radius = Math.min(this.maxRadius, Math.max(this.minRadius, this.radius + event.deltaY * this.zoomSpeed));
            this.update();
        };
        canvas.addEventListener("pointerdown", onPointerDown);
        canvas.addEventListener("pointermove", onPointerMove);
        canvas.addEventListener("pointerup", onPointerUp);
        canvas.addEventListener("pointercancel", onPointerCancel);
        canvas.addEventListener("pointerleave", onPointerLeave);
        canvas.addEventListener("wheel", onWheel);
        this.cleanup.push(() => canvas.removeEventListener("pointerdown", onPointerDown));
        this.cleanup.push(() => canvas.removeEventListener("pointermove", onPointerMove));
        this.cleanup.push(() => canvas.removeEventListener("pointerup", onPointerUp));
        this.cleanup.push(() => canvas.removeEventListener("pointercancel", onPointerCancel));
        this.cleanup.push(() => canvas.removeEventListener("pointerleave", onPointerLeave));
        this.cleanup.push(() => canvas.removeEventListener("wheel", onWheel));
    }
    dispose() {
        for (const fn of this.cleanup) {
            fn();
        }
        this.cleanup = [];
        this.canvas = null;
    }
}
//# sourceMappingURL=camera.js.map