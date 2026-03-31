const video = document.getElementById('webcam');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const captureBtn = document.getElementById('capture-btn');
const studentIdInput = document.getElementById('student_id');
const msgBox = document.getElementById('enroll-message');

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
        });
    } catch (err) {
        showMessage("Error: Camera Access Denied. Please check permissions.", "error");
    }
}

function showMessage(msg, type) {
    msgBox.textContent = msg;
    msgBox.className = `message-box ${type}`;
}

captureBtn.addEventListener('click', async () => {
    const studentId = studentIdInput.value.trim().toUpperCase();
    
    if (!studentId) {
        showMessage("Please enter a Student ID.", "error");
        return;
    }
    
    // Draw current frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.9); // High quality for enrollment
    
    captureBtn.disabled = true;
    captureBtn.textContent = "Processing...";
    showMessage("Analyzing face...", "");
    msgBox.classList.remove('error', 'success');
    msgBox.style.display = 'block';

    try {
        const response = await fetch('/api/enroll_frame', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                student_id: studentId,
                image: dataUrl
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showMessage(data.error || "An error occurred.", "error");
        } else {
            showMessage(data.success, "success");
            studentIdInput.value = ""; // Clear input on success
        }
    } catch (error) {
        showMessage("Network error. Make sure the server is running.", "error");
    } finally {
        captureBtn.disabled = false;
        captureBtn.textContent = "Link Face to Profile";
    }
});

// Start
setupCamera();
