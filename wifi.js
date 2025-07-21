// static/results_upload.js

document.addEventListener("DOMContentLoaded", () => {
    // --- Element Selectors ---
    const uploadButton = document.getElementById("uploadToAdminButton");
    const scorecardElement = document.getElementById("scorecard");
    const profileInfoElement = document.getElementById("profile-info");
    const feedbackModal = document.getElementById("feedbackModal");
    const feedbackTitle = document.getElementById("feedbackTitle");
    const feedbackMessage = document.getElementById("feedbackMessage");
    const closeFeedbackButton = document.getElementById("closeFeedbackModal");

    // --- State Variable ---
    let completedExamData = null;

    // --- Initialize Socket.IO ---
    const socket = io();

    socket.on('connect', () => console.log("Socket connected for result upload."));
    socket.on('disconnect', () => console.warn("Socket disconnected."));

    // Listen for the final confirmation from the server
    socket.on('file_received', (response) => {
        if (response.error) {
            showFeedback("Upload Failed", response.error);
        } else {
            showFeedback("Success!", "Your results have been successfully sent to the admin.");
        }
        uploadButton.disabled = false;
        uploadButton.textContent = "Send to Admin"; // Reset button text/icon if needed
    });

    /**
     * Fetches the final score and details when the page loads.
     */
    async function fetchFinalResults() {
        try {
            const response = await fetch('/get_score');
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to load results.');
            }
            completedExamData = await response.json(); // Store data for later use

            const { student_details, student_score } = completedExamData;
            const questionLength = student_details.question_length;

            if (student_score !== undefined && questionLength !== undefined) {
                scorecardElement.textContent = `${student_score} / ${questionLength}`;
            } else {
                scorecardElement.textContent = "N/A";
            }
            profileInfoElement.textContent = `${student_details.name} (${student_details.class})`;
            
            uploadButton.disabled = false;

        } catch (error) {
            scorecardElement.textContent = "Error";
            profileInfoElement.textContent = `Could not load results: ${error.message}`;
            uploadButton.disabled = true;
        }
    }

    /**
     * Handles the "Upload to Admin" button click.
     */
    function handleUploadClick() {
        if (!completedExamData) {
            showFeedback("Error", "Result data is not available to send.");
            return;
        }
        
        uploadButton.disabled = true;
        // If your button contained an icon, you would replace it with a spinner here.
        // For simplicity, we just show a modal.
        showFeedback("Sending...", "Your results are being sent to the administrator.");

        const { student_details, student_score, student_answers, extracted_answers } = completedExamData;
        
        const fileContent = [
            `Name: ${student_details.name || 'N/A'}`,
            `Class: ${student_details.class || 'N/A'}`,
            `Subject: ${student_details.subject || 'N/A'}`,
            `Score: ${student_score} out of ${student_details.question_length || 'N/A'}`,
            '',
            `Student Answers: ${formatAnswers(student_answers)}`,
            `Correct Answers: ${formatAnswers(extracted_answers)}`
        ].join('\n');

        const filename = `${student_details.name}_${student_details.class}_results.txt`;

        socket.emit('upload_file_to_admin', {
            filename: filename,
            filedata: fileContent
        });
    }

    function formatAnswers(answers) {
        if (!answers || typeof answers !== 'object') return 'N/A';
        return Object.entries(answers)
            .sort((a, b) => parseInt(a[0].substring(1)) - parseInt(b[0].substring(1)))
            .map(([question, answer]) => `${question.substring(1)}${answer}`)
            .join(' ');
    }
    
    function showFeedback(title, message) {
        feedbackTitle.textContent = title;
        feedbackMessage.textContent = message;
        feedbackModal.classList.remove('hidden');
    }

    // --- Event Listeners ---
    uploadButton.addEventListener("click", handleUploadClick);
    closeFeedbackButton.addEventListener("click", () => {
        feedbackModal.classList.add('hidden');
    });

    // --- Initial Load ---
    uploadButton.disabled = true; // Disabled until data is loaded
    fetchFinalResults();
});