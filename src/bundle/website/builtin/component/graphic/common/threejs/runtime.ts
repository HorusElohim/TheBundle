import { loadThreeModule } from "./module.js";

type RuntimeTick = (ctx: { now: number; runtime: ThreeRuntime }) => void;

export type ThreeRuntimeOptions = {
    canvas: HTMLCanvasElement;
    fov?: number;
    near?: number;
    far?: number;
    antialias?: boolean;
    alpha?: boolean;
    pixelRatioCap?: number;
    cameraPosition?: { x: number; y: number; z: number };
    cameraLookAt?: { x: number; y: number; z: number };
};

export class ThreeRuntime {
    three: any;
    scene: any;
    camera: any;
    renderer: any;
    canvas: HTMLCanvasElement | null;
    resizeObserver: ResizeObserver | null;
    frame: number | null;
    tick: RuntimeTick | null;

    constructor() {
        this.three = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.canvas = null;
        this.resizeObserver = null;
        this.frame = null;
        this.tick = null;
    }

    async init(options: ThreeRuntimeOptions) {
        const THREE = await loadThreeModule();
        this.three = THREE;
        this.canvas = options.canvas;
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(options.fov ?? 40, 1, options.near ?? 0.1, options.far ?? 100);

        const cameraPosition = options.cameraPosition ?? { x: 0, y: 0, z: 4 };
        this.camera.position.set(cameraPosition.x, cameraPosition.y, cameraPosition.z);
        const cameraLookAt = options.cameraLookAt ?? { x: 0, y: 0, z: 0 };
        this.camera.lookAt(cameraLookAt.x, cameraLookAt.y, cameraLookAt.z);

        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: options.antialias ?? true,
            alpha: options.alpha ?? true,
        });
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, options.pixelRatioCap ?? 2));

        this.resize();
        this.resizeObserver = new ResizeObserver(() => this.resize());
        this.resizeObserver.observe(this.canvas);
    }

    resize() {
        if (!this.renderer || !this.camera || !this.canvas) {
            return;
        }
        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;
        this.renderer.setSize(width, height, false);
        this.camera.aspect = width / Math.max(height, 1);
        this.camera.updateProjectionMatrix();
    }

    start(tick: RuntimeTick) {
        this.stop();
        this.tick = tick;
        const render = () => {
            const now = performance.now();
            this.tick?.({ now, runtime: this });
            this.renderer?.render(this.scene, this.camera);
            this.frame = window.requestAnimationFrame(render);
        };
        render();
    }

    stop() {
        if (this.frame != null) {
            window.cancelAnimationFrame(this.frame);
            this.frame = null;
        }
    }

    dispose() {
        this.stop();
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
            this.resizeObserver = null;
        }
    }
}
