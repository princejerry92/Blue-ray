// In your static/profile.js file
document.addEventListener("DOMContentLoaded", async () => {
    const socket = io();
    // Add soket io event 
    socket.on('connect', () => {
        console.log('Socket.IO connected.');
        elements.socketIndicator.style.color = 'green';
        displayMessage('Connected to server. Please log in as an admin to receive results.', 'info');
        // If we have a token from a previous login, try to authenticate
        if (adminToken) {
            authenticateSocket();
        }
    });

    socket.on('disconnect', () => {
        console.warn('Socket.IO disconnected.');
        elements.socketIndicator.style.color = 'brown';
        displayMessage('Disconnected from server. Real-time updates are off.', 'error');
    });

    // Main event listener for receiving new result files from students
    socket.on('file_received', (data) => {
        console.log('New result file received:', data);
        if (data.filename) {
            addResultRow(data.filename);
            updateNotificationBadge(++newResultsCount);
            playNotificationSound();
        }
    });
    try {
        // --- KEY CHANGE: Call the same /get_score endpoint ---
        const response = await fetch('/get_score');

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        // --- The rest of your logic works perfectly with the new endpoint's data ---

        // Extract student details
        const studentDetails = data.student_details;
        const studentScore = data.student_score;
        const questionLength = studentDetails.question_length; // This is now available

        // Check if data is valid before populating
        if (!studentDetails || studentScore === undefined || questionLength === undefined) {
            throw new Error("Incomplete data received from server.");
        }

        // Populate the student details on the profile card
        document.getElementById('studentName').textContent = studentDetails.name || "N/A";
        
        // The original HTML didn't have a place for the exam number from the student form,
        // so we'll check if the student_details contains the exam_code they entered.
        // NOTE: The student form doesn't have an "exam_number" field anymore.
        // We will assume the studentDetails object from the form does not have 'exam_number'.
        // Let's hide it if it's not present.
        const examNumberEl = document.getElementById('examNumber');
        if (studentDetails.exam_code) {
            examNumberEl.textContent = `Exam Number: ${studentDetails.exam_code}`;
        } else {
            examNumberEl.style.display = 'none'; // Hide if not available
        }
        
        document.getElementById('studentClass').textContent = studentDetails.class || "N/A";
        document.getElementById('studentSubject').textContent = studentDetails.subject || "N/A";
        document.getElementById('studentScore').textContent = `${studentScore} out of ${questionLength}`;

    } catch (error) {
        console.error("Error fetching profile data:", error);
        // Provide user-friendly feedback on the page itself
        document.getElementById('studentName').textContent = "Error";
        document.getElementById('studentScore').textContent = "Could not load profile.";
        document.getElementById('studentClass').textContent = "N/A";
        document.getElementById('studentSubject').textContent = "N/A";
        document.getElementById('examNumber').textContent = error.message;
    }
});