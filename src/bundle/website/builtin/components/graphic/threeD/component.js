const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const lerp = (a, b, t) => a + (b - a) * t;
function bootGraphic3D(root) {
    const canvas = root.querySelector('[data-role="canvas"]');
    const grid = root.querySelector(".graphic-three-d__grid");
    const fpsLabel = root.querySelector('[data-role="fps"]');
    const countLabel = root.querySelector('[data-role="count"]');
    if (!canvas)
        return;
    const ctx = canvas.getContext("2d");
    if (!ctx)
        return;
    const dprCap = 2;
    const state = { width: 0, height: 0, raf: 0, last: 0, fps: 0, shiftX: 0, shiftY: 0 };
    const pointer = { x: 0.5, y: 0.5 };
    const stars = [];
    const starCount = 190;
    for (let i = 0; i < starCount; i += 1) {
        stars.push({
            x: (Math.random() - 0.5) * 2,
            y: (Math.random() - 0.5) * 2,
            z: 0.12 + Math.random() * 1.6,
            speed: 0.12 + Math.random() * 0.35,
        });
    }
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
    const project = (star) => {
        const depth = 1 / star.z;
        const x = (star.x + state.shiftX * 0.24) * depth;
        const y = (star.y + state.shiftY * 0.2) * depth;
        const sx = state.width * 0.5 + x * state.width * 0.42;
        const sy = state.height * 0.44 + y * state.height * 0.36;
        return { sx, sy, depth };
    };
    const handleMove = (event) => {
        const rect = root.getBoundingClientRect();
        pointer.x = clamp((event.clientX - rect.left) / rect.width, 0, 1);
        pointer.y = clamp((event.clientY - rect.top) / rect.height, 0, 1);
    };
    const resetStar = (star) => {
        star.x = (Math.random() - 0.5) * 2.2;
        star.y = (Math.random() - 0.5) * 1.6;
        star.z = 1.6;
    };
    const draw = (now) => {
        if (!state.last)
            state.last = now;
        const dt = Math.min((now - state.last) / 1000, 0.033);
        state.last = now;
        state.fps = lerp(state.fps || 60, 1 / Math.max(dt, 0.001), 0.08);
        state.shiftX = lerp(state.shiftX, pointer.x - 0.5, 0.04);
        state.shiftY = lerp(state.shiftY, pointer.y - 0.5, 0.04);
        const w = state.width;
        const h = state.height;
        const bg = ctx.createLinearGradient(0, 0, 0, h);
        bg.addColorStop(0, "#07182c");
        bg.addColorStop(0.55, "#020812");
        bg.addColorStop(1, "#000207");
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, w, h);
        const nebula = ctx.createRadialGradient(w * 0.35, h * 0.2, 10, w * 0.4, h * 0.3, w * 0.6);
        nebula.addColorStop(0, "hsla(198, 100%, 68%, 0.35)");
        nebula.addColorStop(0.4, "hsla(224, 100%, 64%, 0.1)");
        nebula.addColorStop(1, "hsla(220, 100%, 64%, 0)");
        ctx.fillStyle = nebula;
        ctx.fillRect(0, 0, w, h);
        for (const star of stars) {
            star.z -= star.speed * dt;
            if (star.z <= 0.08)
                resetStar(star);
            const { sx, sy, depth } = project(star);
            if (sx < -40 || sx > w + 40 || sy < -40 || sy > h + 40) {
                resetStar(star);
                continue;
            }
            const size = clamp(depth * 2.3, 0.6, 5.5);
            const alpha = clamp(depth * 0.45, 0.18, 0.95);
            const tailX = sx - star.x * 12 * depth;
            const tailY = sy - star.y * 8 * depth;
            ctx.strokeStyle = `hsla(198, 100%, 80%, ${alpha * 0.55})`;
            ctx.lineWidth = clamp(size * 0.45, 0.4, 1.8);
            ctx.beginPath();
            ctx.moveTo(tailX, tailY);
            ctx.lineTo(sx, sy);
            ctx.stroke();
            ctx.fillStyle = `hsla(202, 100%, 92%, ${alpha})`;
            ctx.beginPath();
            ctx.arc(sx, sy, size, 0, Math.PI * 2);
            ctx.fill();
        }
        if (grid) {
            const tx = state.shiftX * 22;
            const ty = state.shiftY * 14;
            grid.style.transform = `perspective(320px) rotateX(66deg) translate(${tx}px, ${ty}px)`;
        }
        if (fpsLabel)
            fpsLabel.textContent = `${Math.round(state.fps)}`;
        if (countLabel)
            countLabel.textContent = `${stars.length}`;
        state.raf = requestAnimationFrame(draw);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(root);
    root.addEventListener("pointermove", handleMove);
    root.addEventListener("pointerleave", () => {
        pointer.x = 0.5;
        pointer.y = 0.5;
    });
    resize();
    state.raf = requestAnimationFrame(draw);
}
for (const element of document.querySelectorAll(".graphic-three-d__surface")) {
    bootGraphic3D(element);
}
//# sourceMappingURL=component.js.map