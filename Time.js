document.addEventListener('DOMContentLoaded', function() {
    const hoursInput = document.getElementById('hours');
    const minutesInput = document.getElementById('minutes');
    const secondsInput = document.getElementById('seconds');
    const resetBtn = document.getElementById('resetBtn');
    const saveBtn = document.getElementById('saveBtn');
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


    function resetInputs() {
        console.log('Reset button clicked');
        hoursInput.value = '';
        minutesInput.value = '';
        secondsInput.value = '';
    }

    function saveTime() {
        console.log('Save button clicked');
        const hours = parseInt(hoursInput.value) || 0;
        const minutes = parseInt(minutesInput.value) || 0;
        const seconds = parseInt(secondsInput.value) || 0;

        const totalSeconds = hours * 3600 + minutes * 60 + seconds;

        console.log('Sending request to /Timer with totalSeconds:', totalSeconds);

        fetch('/Timer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'set_time': totalSeconds
            }),
            credentials: 'include'
        })
        .then(response => {
            console.log('Response received:', response);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(data => {
            console.log('Data received:', data);
            alert('Time saved successfully!');
            window.location.href = '/Admin2';  // Redirect to Admin2 page
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An error occurred while saving the time.');
        });
    }

    resetBtn.addEventListener('click', resetInputs);
    saveBtn.addEventListener('click', saveTime);
});