const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const videoInput = document.getElementById('videoInput');
const fileNameDisplay = document.getElementById('fileName');
const btnStart = document.getElementById('btnStart');
const btnStop = document.getElementById('btnStop');
const videoFeed = document.getElementById('videoFeed');
const fpsValue = document.getElementById('fpsValue');
const vehicleCount = document.getElementById('vehicleCount');
const alertsContainer = document.getElementById('alertsContainer');
const placeholderText = document.getElementById('placeholderText');

let socket;
let currentFilename = null;
const BACKEND_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

// 1. Connect WebSocket
function connectWebSocket() {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        statusIndicator.classList.add('connected');
        statusText.textContent = 'Connected';
        console.log('WebSocket Connected');
    };

    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);

        // Handle Status Messages
        if (message.status === 'complete' || message.status === 'finished') {
            alert('Processing Complete');
            return;
        }

        if (message.error) {
            alert('Error: ' + message.error);
            return;
        }

        // Handle Data Stream
        if (message.image) {
            // Update Image
            videoFeed.src = 'data:image/jpeg;base64,' + message.image;
            placeholderText.style.display = 'none';

            // Update Stats
            if (message.fps) fpsValue.textContent = message.fps;
            if (message.vehicles) vehicleCount.textContent = message.vehicles.length;

            // Handle Alerts
            if (message.alerts && message.alerts.length > 0) {
                message.alerts.forEach(alertText => {
                    addAlert(alertText);
                });
            }
        }
    };

    socket.onclose = () => {
        statusIndicator.classList.remove('connected');
        statusText.textContent = 'Disconnected';
        setTimeout(connectWebSocket, 3000); // Reconnect
    };
}

// 2. File Upload
videoInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    fileNameDisplay.textContent = file.name;
    const formData = new FormData();
    formData.append('file', file);

    try {
        btnStart.disabled = true;
        const response = await fetch(`${BACKEND_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (response.ok) {
            currentFilename = result.filename;
            btnStart.disabled = false;
            console.log('Upload successful:', currentFilename);
        } else {
            console.error('Upload failed');
        }
    } catch (err) {
        console.error('Error uploading file:', err);
    }
});

// 3. Start Processing
btnStart.addEventListener('click', () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        alert('WebSocket not connected');
        return;
    }
    if (!currentFilename) {
        alert('Please upload a video first');
        return;
    }

    // Send Start Command
    socket.send(JSON.stringify({
        command: 'start',
        filename: currentFilename
    }));

    btnStart.disabled = true;
    btnStop.disabled = false;
    alertsContainer.innerHTML = ''; // Clear old alerts
});

// 4. Stop Processing (Refresh page for now as easiest way to reset server loop state if needed)
btnStop.addEventListener('click', () => {
    window.location.reload();
});

// Helper: Add Alert
function addAlert(text) {
    const div = document.createElement('div');
    div.className = 'alert-item';
    div.textContent = text;
    alertsContainer.prepend(div);

    // Keep list short
    if (alertsContainer.children.length > 20) {
        alertsContainer.removeChild(alertsContainer.lastChild);
    }
}

// Initialize
connectWebSocket();
