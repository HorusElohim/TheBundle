if (window.WebSocket) {
    const ws = new WebSocket('ws://127.0.0.1:8000/ws/youtube/download_track');

    ws.onopen = function () {
        console.log('WebSocket connection established');
    };

    ws.onmessage = function (event) {
        const data = JSON.parse(event.data);
        console.log('Message from server:', data);

        const metadataContainer = document.getElementById("metadata-container");
        const progressContainer = document.getElementById("progress-container");
        const progressBar = document.getElementById("download-progress");
        const progressInfo = document.getElementById("progress-info");
        const trackTitle = document.getElementById("track-title");
        const trackAuthor = document.getElementById("track-author");
        const trackThumbnail = document.getElementById("track-thumbnail");

        // Handle the different types of messages
        switch (data.type) {
            case 'metadata':
                metadataContainer.style.display = 'block';
                trackAuthor.textContent = data.author;
                trackTitle.textContent = data.title;
                trackThumbnail.src = data.thumbnail_url;
                break;
            case 'downloader_start':
                progressBar.max = data.total;
                progressBar.value = 0; // Reset progress bar for new download
                progressContainer.style.display = 'block'; // Show the progress bar
                progressInfo.innerText = `Preparing to download... Total size: ${data.total} bytes`;
                break;
            case 'downloader_update':
                progressBar.value += data.progress; // Increment the progress bar value
                const percentage = (progressBar.value / progressBar.max) * 100;
                progressInfo.innerText = `Downloaded: ${progressBar.value} bytes (${percentage.toFixed(2)}%)`;
                break;
            case 'downloader_end':
                progressInfo.innerText = "Download completed!";
                progressBar.value = progressBar.max; // Ensure the progress bar shows as full
                break;
            case 'info':
                progressInfo.innerText = `${data.info_message}`;
                break;
            case "file_ready":
                const link = document.createElement('a');
                link.href = data.url;
                link.download = data.filename;
                link.target = '_blank';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            case 'completed':
                progressBar.value = 0;
                progressBar.max = 100;
                progressContainer.style.display = 'none';
                progressInfo.innerText = '';
                trackAuthor.textContent = "";
                trackTitle.textContent = "";
                trackThumbnail.src = "";
                metadataContainer.style.display = 'none';
                // Log the completion
                console.log('Download process completed and UI cleaned up.');
                ws.close();
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    };

    ws.onerror = function (error) {
        console.log('WebSocket Error: ', error);
    };

    ws.onclose = function (event) {
        console.log('WebSocket connection closed:', event.reason, 'Code:', event.code);
    };

    document.getElementById('download-btn').addEventListener('click', function () {
        const youtubeUrl = document.getElementById('youtube-url').value;
        const format = document.querySelector('input[name="format"]:checked').value;
        console.log(`Download button clicked. URL: ${youtubeUrl}, Format: ${format}`);

        // Send a message to start the download
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ 'youtube_url': youtubeUrl, 'format': format }));
            console.log('Request sent to start download.');
        }
        else {
            console.log("Request can't be sent, WebSocketState:", ws.readyState);
        }
    });
} else {
    console.log('Your browser does not support WebSocket.');
}