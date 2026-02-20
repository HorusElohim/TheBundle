type EffectUpdater = (item: any, progress: number, now: number) => void;
type EffectDisposer = (item: any) => void;

export class TransientEffectStore {
    items: any[];
    updater: EffectUpdater;
    disposer: EffectDisposer;

    constructor(updater: EffectUpdater, disposer: EffectDisposer) {
        this.items = [];
        this.updater = updater;
        this.disposer = disposer;
    }

    add(item: any) {
        this.items.push(item);
    }

    tick(now: number) {
        const alive: any[] = [];
        for (const item of this.items) {
            const born = Number(item?.userData?.born ?? now);
            const ttl = Number(item?.userData?.ttl ?? 0);
            if (!Number.isFinite(ttl) || ttl <= 0) {
                alive.push(item);
                continue;
            }
            const progress = (now - born) / ttl;
            if (progress >= 1) {
                this.disposer(item);
                continue;
            }
            this.updater(item, progress, now);
            alive.push(item);
        }
        this.items = alive;
    }

    clear() {
        for (const item of this.items) {
            this.disposer(item);
        }
        this.items = [];
    }
}
