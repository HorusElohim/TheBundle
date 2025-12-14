const iframe = document.getElementById("excalidraw-embed");
if (iframe && !iframe.src) {
  const path = window.location.pathname;
  const base = path.endsWith("/") ? path.slice(0, -1) : path;
  iframe.src = `${base}/excalidraw-web/index.html`;
}
