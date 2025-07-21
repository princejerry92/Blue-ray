document.addEventListener('DOMContentLoaded', function() {
    const openButton = document.getElementById('open');
    const examModal = document.getElementById('examModal');
    const examDetails = document.getElementById('examDetails');
    const cancelExam = document.getElementById('cancelExam');
    const startExam = document.getElementById('startExam');
    //const startExamButton = document.getElementById('startExam');

    if (!openButton || !examModal || !examDetails || !cancelExam || !startExam) {
        console.error('One or more required elements are missing.');
        return;
    }

    openButton.addEventListener('click', function() {
        fetch('/viewer')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log('Received data:', data);  // Debug log
                let detailsHTML = '<h2 class="text-xl text-orange-500 font-bold mb-4">Exam Details</h2><ul class="list-disc list-inside">';
                
                if (data.message) {
                    console.log('No exam details found.');  // Debug log
                    detailsHTML += `<li>${data.message}</li>`;
                } else {
                    console.log('Exam details found:', data);  // Debug log
                    // Process data_store contents
                    for (const [key, value] of Object.entries(data)) {
                        if (typeof value === 'object' && value !== null) {
                            detailsHTML += `<li class="mb-2"><strong>${key}:</strong><ul class="ml-4">`;
                            for (const [subKey, subValue] of Object.entries(value)) {
                                detailsHTML += `<li>${subKey}: ${subValue}</li>`;
                            }
                            detailsHTML += '</ul></li>';
                        } else {
                            detailsHTML += `<li class="mb-2"><strong>${key}:</strong> ${value}</li>`;
                        }
                    }
                }
                
                detailsHTML += '</ul>';
                examDetails.innerHTML = detailsHTML;
                console.log('Updated examDetails innerHTML:', detailsHTML);  // Debug log
                examModal.style.display = 'block';
                console.log('Modal display set to block');  // Debug log
            })
            .catch(error => {
                console.error('Error:', error);
                examDetails.innerHTML = '<p class="text-red-500">An error occurred while fetching exam details.</p>';
                examModal.style.display = 'block';
            });
    });

    cancelExam.addEventListener('click', function() {
        examModal.style.display = 'none';
    });

    startExam.addEventListener('click', function() {
        alert('Starting the exam...');
        examModal.style.display = 'none';
        // Add your exam start logic here
    });

    window.addEventListener('click', function(event) {
        if (event.target === examModal) {
            examModal.style.display = 'none';
        }
    });
   
});