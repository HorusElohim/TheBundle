# ThreeJS Common Frontend Library

This folder is a composable baseline for all future Three.js experiences in website websocket components.

## Modules

- `module.ts`: dynamic loader boundary for Three.js and RGBE loaders.
- `assets.ts`: shared texture/HDR loading helpers with graceful fallback.
- `runtime.ts`: scene/camera/renderer lifecycle with resize + animation loop.
- `camera.ts`: reusable spherical camera rig with pointer + wheel controls.
- `effects.ts`: transient effect store for ttl-driven render effects.
- `primitives.ts`: reusable 3D primitives/helpers (arc curves, sphere mesh, geo projection).
- `index.ts`: public API entrypoint.

## Design Principles

- Single responsibility per module.
- Composition over inheritance.
- Small interfaces with explicit lifecycle (`init`, `start`, `stop`, `dispose`).
- No component-specific assumptions in common code.

## Usage Sketch

```ts
import { ThreeRuntime, SphericalCameraRig, loadTexture } from "./threejs/index.js";

const runtime = new ThreeRuntime();
await runtime.init({ canvas, cameraPosition: { x: 0, y: 0, z: 6 } });

const rig = new SphericalCameraRig(runtime.camera, { radius: 6, minRadius: 3, maxRadius: 12 });
rig.bind(canvas);

runtime.start(({ now }) => {
    // update scene objects or effect stores
});
```
