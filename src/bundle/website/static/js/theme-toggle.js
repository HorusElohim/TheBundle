(() => {
    const key = "bundle-theme";
    const root = document.documentElement;
    const prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
    const saved = localStorage.getItem(key);
    const theme = saved || (prefersLight ? "light" : "dark");
    const apply = (value) => root.setAttribute("data-theme", value);
    apply(theme);

    const button = document.getElementById("theme-toggle");
    if (!button) {
        return;
    }
    button.textContent = theme === "light" ? "Dark mode" : "Light mode";
    button.addEventListener("click", () => {
        const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
        apply(next);
        localStorage.setItem(key, next);
        button.textContent = next === "light" ? "Dark mode" : "Light mode";
    });
})();

