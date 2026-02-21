import { getWebsiteRuntime } from "./site.js";
const trimLeadingSlashes = (value) => String(value || "").replace(/^\/+/, "");
const appendPath = (prefix, path) => {
    const cleanPath = trimLeadingSlashes(path);
    return cleanPath ? `${prefix}/${cleanPath}` : prefix;
};
export const staticUrl = (path) => appendPath(getWebsiteRuntime().mounts.static, path);
export const componentsUrl = (path) => appendPath(getWebsiteRuntime().mounts.components, path);
//# sourceMappingURL=urls.js.map