export type RuntimeNotifier = {
    connecting(): void;
    connected(): void;
    disconnected(): void;
    error(): void;
};

export type WebsiteRuntimeConfig = {
    mounts: {
        static: string;
        components: string;
    };
    assetVersion: string;
};

export type WsNotifier = (label?: string) => RuntimeNotifier;

const DEFAULT_RUNTIME_CONFIG: WebsiteRuntimeConfig = {
    mounts: {
        static: "/static",
        components: "/components-static",
    },
    assetVersion: "dev",
};

const normalizeMount = (value: string, fallback: string): string => {
    const normalized = String(value || "").trim();
    if (!normalized.startsWith("/")) {
        return fallback;
    }
    if (normalized.length > 1) {
        return normalized.replace(/\/+$/, "");
    }
    return fallback;
};

export const getWebsiteRuntime = (): WebsiteRuntimeConfig => {
    const runtime = window.__BUNDLE_WEBSITE_RUNTIME__;
    if (!runtime || typeof runtime !== "object") {
        return DEFAULT_RUNTIME_CONFIG;
    }
    const mounts = runtime.mounts || DEFAULT_RUNTIME_CONFIG.mounts;
    return {
        mounts: {
            static: normalizeMount(mounts.static, DEFAULT_RUNTIME_CONFIG.mounts.static),
            components: normalizeMount(mounts.components, DEFAULT_RUNTIME_CONFIG.mounts.components),
        },
        assetVersion: String(runtime.assetVersion || DEFAULT_RUNTIME_CONFIG.assetVersion),
    };
};

declare global {
    interface Window {
        __BUNDLE_WEBSITE_RUNTIME__?: WebsiteRuntimeConfig;
        wsNotifier?: WsNotifier;
    }
}

