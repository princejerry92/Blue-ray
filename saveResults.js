
document.addEventListener("DOMContentLoaded", () => {
    const uploadButton = document.querySelector(".w-full.bg-orange-500");
    const modal = document.getElementById("modal");
    const modalTitle = document.getElementById("modalTitle");
    const modalMessage = document.getElementById("modalMessage");
    const modalClose = document.getElementById("modalClose");
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
    
    // Click event to upload results
    uploadButton.addEventListener("click", async () => {
        try {
            // Show loading spinner
            uploadButton.classList.add("loading");

            // Fetch the required data (e.g., from dataStore or an endpoint)
            const response = await fetch('/get_score');  // Assuming data comes from this endpoint
            const data = await response.json();
            
            // Post data to the /Resultbank endpoint
            const resultResponse = await fetch('/Resultbank', {
                method: 'POST',
                credentials: 'include',

                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    student_details: data.student_details,
                    student_answers: data.student_answers,
                    extracted_answers: data.extracted_answers
                })
            });

            if (!resultResponse.ok) {
                throw new Error(`Error: ${resultResponse.status} - ${resultResponse.statusText}`);
            }

            const resultData = await resultResponse.json();

            // Show success modal
            showModal("Success", "Results have been uploaded successfully!");

        } catch (error) {
            console.error(error);
            showModal("Error", "Failed to upload results. Please try again.");
        } finally {
            // Hide loading spinner
            uploadButton.classList.remove("loading");
        }
    });

    // Function to show modal
    function showModal(title, message) {
        modalTitle.textContent = title;
        modalMessage.textContent = message;
        modal.classList.remove("hidden");
    }

    // Close modal event
    modalClose.addEventListener("click", () => {
        modal.classList.add("hidden");
    });
});
