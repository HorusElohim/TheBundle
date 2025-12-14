const EMBED_HOST = "https://excalidraw.com/";

const iframe = document.getElementById("excalidraw-embed");
if (iframe) {
  const params = new URLSearchParams({
    embed: "1",
    theme: "dark",
  });

  iframe.src = `${EMBED_HOST}?${params.toString()}`;
}
