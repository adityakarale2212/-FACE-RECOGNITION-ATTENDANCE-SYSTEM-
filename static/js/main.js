const video = document.getElementById('webcam');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

const nameEl = document.getElementById('id-name');
const blinksEl = document.getElementById('id-blinks');
const statusEl = document.getElementById('id-status');

let blinkCount = 0;
let blinkDetected = false;
let isProcessing = false;

// Initialize Webcam
async function setupCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: 640, height: 480 },
            audio: false
        });
        video.srcObject = stream;

        video.addEventListener('loadeddata', () => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            // Start processing loop
            requestAnimationFrame(processFrame);
        });
    } catch (err) {
        console.error("Error accessing webcam:", err);
        statusEl.textContent = "Error: Camera Access Denied";
        statusEl.style.color = "var(--danger)";
    }
}

async function processFrame() {
    if (isProcessing) {
        requestAnimationFrame(processFrame);
        return;
    }

    isProcessing = true;

    // Draw current frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Get base64 jpeg
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);

    try {
        const response = await fetch('/api/process_frame', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: dataUrl,
                blink_counted: blinkCount,
                blink_detected: blinkDetected
            })
        });

        const data = await response.json();

        if (data.error) {
            console.error(data.error);
        } else {
            // Update UI
            nameEl.textContent = data.name;
            blinksEl.textContent = data.blinks;
            statusEl.textContent = data.status;

            // Maintain blink state machine
            blinkCount = data.blinks;
            blinkDetected = data.blink_detected;

            if (data.logged) {
                statusEl.style.color = "var(--success)";
                nameEl.classList.add('highlight');
            } else if (data.status.includes("Waiting") || data.status.includes("Blink")) {
                statusEl.style.color = "var(--text-secondary)";
            } else if (data.status.includes("Unknown")) {
                statusEl.style.color = "var(--danger)";
            }
        }
    } catch (error) {
        console.error('API Error:', error);
    } finally {
        isProcessing = false;
        // Throttle slightly to save CPU, e.g., 20 FPS max
        setTimeout(() => {
            requestAnimationFrame(processFrame);
        }, 50);
    }
}

// Start
setupCamera();
