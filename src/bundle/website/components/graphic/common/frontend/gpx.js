import { WebSocketComponent } from "../../../websocket/base/frontend/ws.js";
import { SphericalCameraRig, ThreeRuntime } from "./threejs/index.js";
export class GpxWebSocketComponent extends WebSocketComponent {
    runtime;
    cameraRig;
    canvas;
    constructor(element) {
        super(element, { reconnectDelayMs: 1500 });
        this.runtime = null;
        this.cameraRig = null;
        this.canvas = element.querySelector('[data-role="canvas"]');
    }
    async initGpxScene(options) {
        this.runtime = new ThreeRuntime();
        await this.runtime.init({
            canvas: options.canvas,
            fov: 40,
            near: 0.1,
            far: 100,
            antialias: true,
            alpha: true,
            pixelRatioCap: 2,
        });
        this.cameraRig = new SphericalCameraRig(this.runtime.camera, {
            radius: options.cameraRadius,
            minRadius: options.cameraMinRadius,
            maxRadius: options.cameraMaxRadius,
        });
        this.cameraRig.bind(options.canvas);
    }
    disposeGpxScene() {
        this.cameraRig?.dispose();
        this.cameraRig = null;
        this.runtime?.dispose();
        this.runtime = null;
    }
}
//# sourceMappingURL=gpx.js.map