// static/Admin2.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const elements = {
        // Main page elements
        downloadsButton: document.getElementById('Downloads'),
        viewResultButton: document.getElementById('viewResult'),
        connectionsButton: document.getElementById('connections'),
        resultUploaderButton: document.getElementById('resultUploader'),
        fileUploaderInput: document.getElementById('fileInput'),
        openExamButton: document.getElementById('open'),
        badge: document.getElementById('badge'),
        // Corrected: get the element first, then add the event listener below
        generateCodeButton: document.getElementById('generateCode'), 

        // Modals
        listModal: document.getElementById('listModal'),
        errorModal: document.getElementById('errorModal'),
        examModal: document.getElementById('examModal'),
        progressModal: document.getElementById('progress-modal'),

        // Modal Content
        fileList: document.getElementById('fileList'),
        errorTitle: document.getElementById('errorTitle'),
        errorMessage: document.getElementById('errorMessage'),
        examDetailsContainer: document.getElementById('examDetails'),
        progressStatus: document.getElementById('progressStatus'),
        progressBar: document.getElementById('progressBar'),
        progressPercentage: document.getElementById('progressPercentage'),
        
        // Modal Buttons
        cancelExamButton: document.getElementById('cancelExam'),
        startExamButton: document.getElementById('startExam'),
    };

    // --- Initialize Socket.IO ---
    // Connects to the server that served the page, no IP needed.
    const socket = io();
    
    // --- Socket.IO Event Handlers ---
    socket.on('connect', () => {
        console.log('Successfully connected to the server.');
        // You can optionally show a connection status update here.
    });

    socket.on('disconnect', () => {
        console.warn('Disconnected from the server.');
    });

    socket.on('file_uploaded', (data) => {
        console.log('New file notification received:', data);
        updateNewFileBadge(true); // Show the "New!" badge
        new Audio("../static/img/assets/message-13716.mp3").play();
    });

    socket.on('upload_progress_ack', (data) => {
        console.log(`Upload progress ack: ${data.filename} - ${data.progress}%`);
        updateUploadProgress(data.progress);
    });

    socket.on('file_received', (data) => {
        if (data.error) {
            showError('Upload Error', data.error);
        } else {
            console.log('Server confirmed file receipt:', data.message);
        }
        hideProgressModal();
    });


    // --- Main Page Event Listeners ---

    // The "Downloads" button now correctly opens the file list modal
    elements.downloadsButton.addEventListener('click', () => {
        fetchAndListFiles();
        updateNewFileBadge(false); // Hide badge after viewing
    });

    // Handle "View Exam Details" button click
    elements.openExamButton.addEventListener('click', fetchAndShowExamDetails);
    
    // Handle "Upload Results" button click
    elements.resultUploaderButton.addEventListener('click', () => {
        elements.fileUploaderInput.click();
    });

    elements.fileUploaderInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            uploadResultFile(file);
        }
    });

    // Corrected: Add event listener for generateCode button outside of the elements object
    if (elements.generateCodeButton) { // Check if the element exists to prevent errors
        elements.generateCodeButton.addEventListener('click', handleGenerateCodeClick);
    }

    // --- Exam Details Modal ---
    elements.cancelExamButton.addEventListener('click', () => {
        elements.examModal.style.display = 'none';
    });
    
    elements.startExamButton.addEventListener('click', () => {
        window.location.href = '/examloader'; // Corrected endpoint from your HTML
    });

    // Add close functionality to all modals
    document.querySelectorAll('.modal .close').forEach(button => {
        button.addEventListener('click', (e) => {
            e.target.closest('.modal').style.display = 'none';
        });
    });

    // --- Core Logic Functions ---

    /**
     * Fetches the list of all available files from the server and populates the list modal.
     */
    async function fetchAndListFiles() {
        try {
            const response = await fetch('/downloads'); // The endpoint that renders the list page
            if (!response.ok) throw new Error(`Server error: ${response.status}`);
            
            // Since `/downloads` returns HTML, we'll parse it to find the files
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            elements.fileList.innerHTML = ''; // Clear previous list
            const fileLinks = doc.querySelectorAll('a[href^="/download/"]');

            if (fileLinks.length === 0) {
                elements.fileList.innerHTML = '<li>No files available for download.</li>';
            } else {
                fileLinks.forEach(link => {
                    const li = document.createElement('li');
                    const newLink = document.createElement('a');
                    newLink.href = link.href;
                    newLink.textContent = link.textContent;
                    newLink.className = 'text-blue-400 hover:underline';
                    newLink.target = '_blank'; // Open in new tab to trigger download
                    li.appendChild(newLink);
                    elements.fileList.appendChild(li);
                });
            }
            elements.listModal.style.display = 'block';

        } catch (error) {
            console.error('Error fetching file list:', error);
            showError('Network Error', 'Could not fetch the list of available files.');
        }
    }

    async function handleGenerateCodeClick() {
        try {
            const response = await fetch('/generate_exam_code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
                // The session cookie is sent automatically by the browser,
                // so no need to send a token in the body.
            });

            const data = await response.json();

            if (!response.ok) {
                // If the server returns an error (4xx or 5xx)
                throw new Error(data.error || 'Failed to generate code.');
            }

            // --- Success! Display the code to the admin ---
            const examCode = data.exam_code;
            alert(`Exam Code Generated! Share this with your students: ${examCode}`);
            
            // You can also display it more nicely in a modal or a dedicated text box.
            // For example:
            // document.getElementById('exam-code-display').textContent = examCode;

        } catch (error) {
            console.error('Error generating exam code:', error);
            alert(`Error: ${error.message}`);
        }
    }

   // In static/Admin2.js, replace the existing function with this one.

/**
 * Fetches the currently configured exam details from the server and displays them.
 */
    async function fetchAndShowExamDetails() {
        try {
            const response = await fetch('/viewer');
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.message || `Server error: ${response.status}`);
            }
            
            const data = await response.json();
            let detailsHTML = '<h2 class="text-xl text-orange-500 font-bold mb-4">Current Exam Configuration</h2>';

            if (data.message) {
                // Handles cases where no exam is configured yet
                detailsHTML += `<p class="text-gray-400">${data.message}</p>`;
            } else {
                detailsHTML += '<ul class="list-disc list-inside space-y-2 text-gray-300">';
                
                // Display exam time if available
                if (data.exam_time) {
                    detailsHTML += `<li><strong>Time Limit:</strong> ${data.exam_time}</li>`;
                } else {
                    detailsHTML += `<li><strong>Time Limit:</strong> Not set</li>`;
                }

                // Display subject details if available
                if (data.subject) {
                    detailsHTML += `<li><strong>Subject:</strong> ${data.subject.subject || 'Not set'}</li>`;
                    detailsHTML += `<li><strong>No. of Questions:</strong> ${data.subject.question_length || 'Not set'}</li>`;
                    detailsHTML += `<li><strong>Question File:</strong> ${data.subject.question_template_filename || 'Not set'}</li>`;
                    detailsHTML += `<li><strong>Answer File:</strong> ${data.subject.answer_template_filename || 'Not set'}</li>`;
                    detailsHTML += `<li><strong>Contains Images:</strong> ${data.subject.contains_images ? 'Yes' : 'No'}</li>`;
                } else {
                    detailsHTML += `<li><strong>Subject Details:</strong> Not set</li>`;
                }

                detailsHTML += '</ul>';
            }

            elements.examDetailsContainer.innerHTML = detailsHTML;
            elements.examModal.style.display = 'block';

        } catch (error) {
            console.error('Error fetching exam details:', error);
            showError('Error', `Could not retrieve exam details: ${error.message}`);
        }
    }

    /**
     * Handles uploading a result file to the admin server.
     * @param {File} file The file to upload.
     */
    function uploadResultFile(file) {
        showProgressModal();
        updateUploadProgress(0);

        const reader = new FileReader();
        reader.onload = (e) => {
            // We just need the file content, no need to Base64 encode here if server doesn't need it
            // However, the original code did it, so we'll stick to it.
            const filedata = e.target.result; // This is the full Data URL
            socket.emit('upload_file_to_admin', {
                filename: file.name,
                filedata: filedata, // Sending the full data URL
            });
            // Simulate progress for visual feedback
            simulateProgress(file.name);
        };
        reader.onerror = (e) => {
            console.error('Error reading file:', e);
            showError('File Error', 'Failed to read the selected file.');
            hideProgressModal();
        };
        reader.readAsDataURL(file); // Reads the file as a Data URL
    }

    // --- Helper & UI Functions ---

    function showError(title, message) {
        elements.errorTitle.textContent = title;
        elements.errorMessage.textContent = message;
        elements.errorModal.style.display = 'block';
    }

    function updateNewFileBadge(show) {
        elements.badge.style.display = show ? 'inline-block' : 'none';
    }
    
    function showProgressModal() {
        elements.progressModal.style.display = 'block';
    }

    function hideProgressModal() {
        elements.progressModal.style.display = 'none';
    }

    function updateUploadProgress(progress) {
        elements.progressStatus.textContent = `Sending... ${progress}%`;
        elements.progressBar.value = progress;
        elements.progressPercentage.textContent = `${progress}%`;
    }

    function simulateProgress(filename) {
        let progress = 0;
        const interval = setInterval(() => {
            progress += 10;
            if (progress >= 100) {
                clearInterval(interval);
                progress = 100;
            }
            updateUploadProgress(progress);
            // We can emit a simulated progress event if needed, but ack is better
            socket.emit('upload_progress', { filename, progress });
        }, 200);
    }
});