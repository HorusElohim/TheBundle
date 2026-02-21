type RuntimeNotifier = {
    connecting(): void;
    connected(): void;
    disconnected(): void;
    error(): void;
};

type WebsiteRuntimeConfig = {
    mounts: {
        static: string;
        components: string;
    };
    assetVersion: string;
};

type WsNotifier = (label?: string) => RuntimeNotifier;

interface Window {
    __BUNDLE_WEBSITE_RUNTIME__?: WebsiteRuntimeConfig;
    wsNotifier?: WsNotifier;
}

