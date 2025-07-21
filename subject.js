// static/subject.js
document.addEventListener('DOMContentLoaded', function() {
    // --- Element Selectors ---
    const subjectInput = document.getElementById('subject');
    const questionLengthInput = document.getElementById('question-length');
    const questionTemplateInput = document.getElementById('question-template');
    const answerTemplateInput = document.getElementById('answer-template');
    const containsImagesCheckbox = document.getElementById('contains-images');
    const resetBtn = document.getElementById('resetBtn');
    const saveSubjectBtn = document.getElementById('saveSubjectBtn');
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

    // --- Event Listeners ---
    resetBtn.addEventListener('click', resetForm);
    saveSubjectBtn.addEventListener('click', saveSubject);

    // --- Functions ---
    
    /**
     * Resets all form inputs to their default state.
     */
    function resetForm() {
        subjectInput.value = '';
        questionLengthInput.value = '';
        questionTemplateInput.value = ''; // This clears the file selection in the input
        answerTemplateInput.value = '';
        containsImagesCheckbox.checked = false;
        console.log("Form has been reset.");
    }

    /**
     * Validates inputs, packages form data, and sends it to the server.
     */
    async function saveSubject() {
        // --- 1. Client-Side Validation ---
        if (!subjectInput.value.trim()) {
            alert('Please enter a subject name.');
            subjectInput.focus();
            return;
        }
        if (!questionLengthInput.value || parseInt(questionLengthInput.value, 10) < 1) {
            alert('Please enter a valid number of questions.');
            questionLengthInput.focus();
            return;
        }
        const questionFile = questionTemplateInput.files[0];
        if (!questionFile) {
            alert('Please upload a question template file.');
            return;
        }
        if (answerTemplateInput.files.length === 0) {
            alert('Please upload an answer template file.');
            return;
        }
        
        // This is the specific validation for the "Contains Images" feature.
        // It provides immediate feedback to the user.
        const containsImages = containsImagesCheckbox.checked;
        if (containsImages && !questionFile.name.toLowerCase().endsWith('.pdf')) {
            alert('When "Contains Images" is checked, the question template must be a PDF file.');
            return;
        }

        // --- 2. Create FormData ---
        const formData = new FormData();
        formData.append('subject', subjectInput.value.trim());
        formData.append('question-length', questionLengthInput.value);
        formData.append('question-template', questionFile);
        formData.append('answer-template', answerTemplateInput.files[0]);
        formData.append('contains-images', containsImages); // Sends 'true' or 'false'

        // --- 3. Disable button to prevent multiple submissions ---
        saveSubjectBtn.disabled = true;
        saveSubjectBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';

        // --- 4. Send to Server ---
        try {
            const response = await fetch('/Subject', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (response.ok) {
                // The server now sends back a 'success' flag which we check.
                if (data.success) {
                    alert('Subject saved successfully! Redirecting...');
                    window.location.href = '/Admin2'; // Redirect on success
                } else {
                    // Handle cases where the server returns a non-error status but a failure message
                    throw new Error(data.message || 'Server indicated an issue.');
                }
            } else {
                // Handle HTTP errors (like 400, 500) and display the server's error message
                throw new Error(data.message || `HTTP error! Status: ${response.status}`);
            }
        } catch (error) {
            console.error('Error saving subject:', error);
            alert(`Failed to save subject: ${error.message}`);
        } finally {
            // --- 5. Re-enable button after the process is complete ---
            saveSubjectBtn.disabled = false;
            saveSubjectBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Save Subject';
        }
    }
});