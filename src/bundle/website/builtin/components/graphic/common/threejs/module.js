const DEFAULT_THREE_MODULE_URL = "https://esm.sh/three@0.161.0";
const DEFAULT_RGBE_LOADER_MODULE_URL = "https://esm.sh/three@0.161.0/examples/jsm/loaders/RGBELoader.js";
let threeModulePromise = null;
export function loadThreeModule(moduleUrl = DEFAULT_THREE_MODULE_URL) {
    if (!threeModulePromise) {
        threeModulePromise = import(moduleUrl);
    }
    return threeModulePromise;
}
export async function loadRgbELoaderModule(moduleUrl = DEFAULT_RGBE_LOADER_MODULE_URL) {
    return import(moduleUrl);
}
export { DEFAULT_RGBE_LOADER_MODULE_URL, DEFAULT_THREE_MODULE_URL };
//# sourceMappingURL=module.js.map