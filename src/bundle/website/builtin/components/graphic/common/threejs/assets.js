import { DEFAULT_RGBE_LOADER_MODULE_URL, loadRgbELoaderModule } from "./module.js";
export function loadTexture(THREE, url, configure) {
    return new Promise((resolve) => {
        const loader = new THREE.TextureLoader();
        loader.load(url, (texture) => {
            configure?.(texture);
            resolve(texture);
        }, undefined, () => resolve(null));
    });
}
export async function loadHdrTexture(url, loaderModuleUrl = DEFAULT_RGBE_LOADER_MODULE_URL) {
    try {
        const { RGBELoader } = await loadRgbELoaderModule(loaderModuleUrl);
        return await new Promise((resolve) => {
            new RGBELoader().load(url, (texture) => resolve(texture), undefined, () => resolve(null));
        });
    }
    catch {
        return null;
    }
}
//# sourceMappingURL=assets.js.map