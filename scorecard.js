// In your scorecard.js file

document.addEventListener("DOMContentLoaded", async () => {
    const scorecardElement = document.getElementById("scorecard");
    const socket = io();
    // Make sure you have an element with id="scorecard" in your HTML
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

    if (!scorecardElement) {
        console.error("Scorecard display element with id='scorecard' not found!");
        return;
    }

    try {
        // --- KEY CHANGE: Call the new, secure /get_score endpoint ---
        const response = await fetch('/get_score');

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Error: ${response.status}`);
        }

        const data = await response.json();
        console.log("Retrieved data from /get_score endpoint:", data);

        // --- The rest of your logic is already correct ---

        // Accessing student score and question length
        const studentScore = data.student_score;
        // The question_length is now nested inside student_details for compatibility
        const questionLength = data.student_details?.question_length;

        console.log("Student Score:", studentScore);
        console.log("Question Length:", questionLength);

        if (studentScore !== undefined && questionLength !== undefined) {
            scorecardElement.textContent = `${studentScore} out of ${questionLength}`;
        } else {
            // This case might happen if marking is still in progress
            scorecardElement.textContent = "Score not yet available.";
        }

        // You can now also use the other data if needed, for example,
        // to show a comparison of student answers vs correct answers.
        // displayAnswerComparison(data.student_answers, data.extracted_answers);

    } catch (error) {
        console.error("Error retrieving score:", error);
        scorecardElement.textContent = `Error: ${error.message}`;
    }
});

