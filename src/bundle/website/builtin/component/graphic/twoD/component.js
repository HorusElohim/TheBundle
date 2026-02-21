const lerp = (a, b, t) => a + (b - a) * t;
function bootGraphic2D(root) {
    const canvas = root.querySelector('[data-role="canvas"]');
    const fpsLabel = root.querySelector('[data-role="fps"]');
    const countLabel = root.querySelector('[data-role="count"]');
    if (!canvas)
        return;
    const ctx = canvas.getContext("2d");
    if (!ctx)
        return;
    const dprCap = 2;
    const particles = [];
    const particleCount = 58;
    for (let i = 0; i < particleCount; i += 1) {
        particles.push({
            x: Math.random(),
            y: Math.random(),
            vx: (Math.random() - 0.5) * 0.16,
            vy: (Math.random() - 0.5) * 0.16,
            radius: 1.5 + Math.random() * 3.2,
            hue: 188 + Math.random() * 45,
        });
    }
    const pointer = { x: 0.5, y: 0.5, active: false };
    const state = { width: 0, height: 0, raf: 0, last: 0, fps: 0 };
    const resize = () => {
        const bounds = root.getBoundingClientRect();
        const dpr = Math.min(window.devicePixelRatio || 1, dprCap);
        state.width = Math.max(1, Math.floor(bounds.width));
        state.height = Math.max(1, Math.floor(bounds.height));
        canvas.width = Math.floor(state.width * dpr);
        canvas.height = Math.floor(state.height * dpr);
        canvas.style.width = `${state.width}px`;
        canvas.style.height = `${state.height}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const handleMove = (event) => {
        const rect = root.getBoundingClientRect();
        pointer.x = (event.clientX - rect.left) / rect.width;
        pointer.y = (event.clientY - rect.top) / rect.height;
        pointer.active = true;
    };
    const draw = (now) => {
        if (!state.last)
            state.last = now;
        const dt = Math.min((now - state.last) / 1000, 0.033);
        state.last = now;
        state.fps = lerp(state.fps || 60, 1 / Math.max(dt, 0.001), 0.08);
        const w = state.width;
        const h = state.height;
        const px = pointer.active ? pointer.x * w : w * 0.5;
        const py = pointer.active ? pointer.y * h : h * 0.5;
        const bg = ctx.createLinearGradient(0, 0, 0, h);
        bg.addColorStop(0, "#081b2d");
        bg.addColorStop(1, "#02060f");
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, w, h);
        for (let i = 0; i < particles.length; i += 1) {
            const p = particles[i];
            p.x += p.vx * dt;
            p.y += p.vy * dt;
            if (p.x < 0 || p.x > 1)
                p.vx *= -1;
            if (p.y < 0 || p.y > 1)
                p.vy *= -1;
            p.x = Math.max(0, Math.min(1, p.x));
            p.y = Math.max(0, Math.min(1, p.y));
        }
        ctx.lineWidth = 1;
        for (let i = 0; i < particles.length; i += 1) {
            const a = particles[i];
            const ax = a.x * w;
            const ay = a.y * h;
            for (let j = i + 1; j < particles.length; j += 1) {
                const b = particles[j];
                const bx = b.x * w;
                const by = b.y * h;
                const dx = ax - bx;
                const dy = ay - by;
                const distance = Math.sqrt(dx * dx + dy * dy);
                if (distance > 130)
                    continue;
                const alpha = 1 - distance / 130;
                ctx.strokeStyle = `hsla(196, 100%, 70%, ${alpha * 0.35})`;
                ctx.beginPath();
                ctx.moveTo(ax, ay);
                ctx.lineTo(bx, by);
                ctx.stroke();
            }
        }
        for (const p of particles) {
            const x = p.x * w;
            const y = p.y * h;
            const dx = x - px;
            const dy = y - py;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const push = Math.max(0, 1 - dist / 180);
            const glow = p.radius + push * 6;
            const g = ctx.createRadialGradient(x, y, 0, x, y, glow * 3);
            g.addColorStop(0, `hsla(${p.hue}, 96%, 72%, 0.9)`);
            g.addColorStop(1, "hsla(204, 100%, 50%, 0)");
            ctx.fillStyle = g;
            ctx.beginPath();
            ctx.arc(x, y, glow * 3, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = `hsla(${p.hue}, 90%, 78%, 0.85)`;
            ctx.beginPath();
            ctx.arc(x, y, glow, 0, Math.PI * 2);
            ctx.fill();
        }
        if (fpsLabel)
            fpsLabel.textContent = `${Math.round(state.fps)}`;
        if (countLabel)
            countLabel.textContent = `${particles.length}`;
        state.raf = requestAnimationFrame(draw);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(root);
    root.addEventListener("pointermove", handleMove);
    root.addEventListener("pointerleave", () => {
        pointer.active = false;
    });
    resize();
    state.raf = requestAnimationFrame(draw);
}
for (const element of document.querySelectorAll(".graphic-two-d__surface")) {
    bootGraphic2D(element);
}
//# sourceMappingURL=component.js.map