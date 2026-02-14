export class TransientEffectStore {
    items;
    updater;
    disposer;
    constructor(updater, disposer) {
        this.items = [];
        this.updater = updater;
        this.disposer = disposer;
    }
    add(item) {
        this.items.push(item);
    }
    tick(now) {
        const alive = [];
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
//# sourceMappingURL=effects.js.map