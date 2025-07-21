
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
                // Fetch the data from the /retriever endpoint
                const response = await fetch('/get_score');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
        
                // Extract student details and answers
                const studentDetails = data.student_details;
                const studentAnswers = data.student_answers;
                const correctAnswers = data.extracted_answers;
                const studentScore = data.student_score;
                const questionLength = studentDetails.question_length;
        
                // Populate the student details
                document.getElementById('studentName').textContent = studentDetails.name || "N/A";
                document.getElementById('studentClass').textContent = studentDetails.class || "N/A";
                document.getElementById('studentSubject').textContent = studentDetails.subject || "N/A";
                document.getElementById('studentScore').textContent = `${studentScore} out of ${questionLength}`;
                document.getElementById('examNumber').textContent = studentDetails.exam_code || "N/A";
        
                // Format and display student's answers in sorted order
                let studentAnswersText = formatAnswers(studentAnswers);
                document.getElementById('studentAnswers').textContent = studentAnswersText.trim();
        
                // Format and display correct answers in sorted order
                let correctAnswersText = formatAnswers(correctAnswers);
                document.getElementById('correctAnswers').textContent = correctAnswersText.trim();
        
            } catch (error) {
                console.error("Error fetching data from /get_score:", error);
                alert("Failed to load results. Please try again.");
            }
        });
        
        function formatAnswers(answers) {
            const sortedEntries = Object.entries(answers).sort((a, b) => {
                const aNumber = parseInt(a[0].slice(1));
                const bNumber = parseInt(b[0].slice(1));
                return aNumber - bNumber;
            });
        
            return sortedEntries.map(([question, answer]) => `${question.slice(1)}${answer}`).join(' ');
        }
    
       