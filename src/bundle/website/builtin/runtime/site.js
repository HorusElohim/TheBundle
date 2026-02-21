const DEFAULT_RUNTIME_CONFIG = {
    mounts: {
        static: "/static",
        components: "/components-static",
    },
    assetVersion: "dev",
};
const normalizeMount = (value, fallback) => {
    const normalized = String(value || "").trim();
    if (!normalized.startsWith("/")) {
        return fallback;
    }
    if (normalized.length > 1) {
        return normalized.replace(/\/+$/, "");
    }
    return fallback;
};
export const getWebsiteRuntime = () => {
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
//# sourceMappingURL=site.js.map