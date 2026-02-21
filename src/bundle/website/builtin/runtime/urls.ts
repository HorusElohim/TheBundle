import { getWebsiteRuntime } from "./site.js";

const trimLeadingSlashes = (value: string): string => String(value || "").replace(/^\/+/, "");

const appendPath = (prefix: string, path: string): string => {
    const cleanPath = trimLeadingSlashes(path);
    return cleanPath ? `${prefix}/${cleanPath}` : prefix;
};

export const staticUrl = (path: string): string => appendPath(getWebsiteRuntime().mounts.static, path);

export const componentsUrl = (path: string): string => appendPath(getWebsiteRuntime().mounts.components, path);

