import { DEFAULT_RGBE_LOADER_MODULE_URL, loadRgbELoaderModule } from "./module.js";

export function loadTexture(THREE: any, url: string, configure?: (texture: any) => void): Promise<any> {
    return new Promise<any>((resolve) => {
        const loader = new THREE.TextureLoader();
        loader.load(
            url,
            (texture: any) => {
                configure?.(texture);
                resolve(texture);
            },
            undefined,
            () => resolve(null)
        );
    });
}

export async function loadHdrTexture(url: string, loaderModuleUrl = DEFAULT_RGBE_LOADER_MODULE_URL): Promise<any> {
    try {
        const { RGBELoader } = await loadRgbELoaderModule(loaderModuleUrl);
        return await new Promise<any>((resolve) => {
            new RGBELoader().load(url, (texture: any) => resolve(texture), undefined, () => resolve(null));
        });
    } catch {
        return null;
    }
}
