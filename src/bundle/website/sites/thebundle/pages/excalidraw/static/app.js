const iframe = document.getElementById("excalidraw-embed");

const resolveBasePath = () => {
  const path = window.location.pathname;
  return path.endsWith("/") ? path.slice(0, -1) : path;
};

const applyThemeToExcalidraw = () => {
  if (!iframe) return;
  const theme = document.documentElement.getAttribute("data-theme") || "dark";
  const basePath = iframe.dataset.base || resolveBasePath();
  iframe.dataset.base = basePath;

  try {
    // Parent storage
    localStorage.setItem("excalidraw-theme", theme);
    // Iframe storage (same origin)
    iframe.contentWindow?.localStorage?.setItem("excalidraw-theme", theme);
  } catch {
    // ignore storage errors
  }

  const url = new URL(`${basePath}/excalidraw-web/index.html`, window.location.origin);
  url.searchParams.set("theme", theme);
  url.searchParams.set("ts", Date.now().toString()); // cache-bust
  if (iframe.src !== url.toString()) {
    iframe.src = url.toString();
  } else {
    // If src already matches, force a reload
    iframe.contentWindow?.location?.reload();
  }
};

applyThemeToExcalidraw();

const observer = new MutationObserver(applyThemeToExcalidraw);
observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
