document.addEventListener('DOMContentLoaded', function () {
    const studentsTableBody = document.querySelector('#studentsTable tbody');
    const resultModal = document.getElementById('resultModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    const closeModalBtn = document.getElementById('closeModalBtn');

    // Delegate click event to all 'view' icons in the table
    studentsTableBody.addEventListener('click', function(event) {
        if (event.target && event.target.classList.contains('fa-eye')) {
            const row = event.target.closest('tr');
            const filename = row.querySelector('td:nth-child(2) .text-gray-900').textContent.trim();  // Adjust this selector based on the table structure

            // Fetch the result from the server
            fetchResult(filename);
        }
    });

    function fetchResult(filename) {
        // Send an AJAX request to the /view_result endpoint
        fetch(`/view_result?filename=${encodeURIComponent(filename)}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                } else {
                    // Show the modal with file contents
                    showModal(data.filename, data.content);
                }
            })
            .catch(error => {
                console.error('Error fetching result:', error);
            });
    }

    function showModal(filename, content) {
        modalTitle.textContent = filename;
    
        // Split the content into separate sections
        const sections = content.split("\n");
        const studentAnswersSection = sections.find(section => section.startsWith("Student Answers:"));
        const correctAnswersSection = sections.find(section => section.startsWith("Correct Answers:"));
        const otherSections = sections.filter(section => !section.startsWith("Student Answers:") && !section.startsWith("Correct Answers:"));
    
        // Create HTML elements for each section
        const otherHtml = otherSections.map(section => `<p>${section}</p>`).join("");
        const studentAnswersHtml = `<h2>Student Answers:</h2><p>${studentAnswersSection.replace("Student Answers:", "").trim()}</p>`;
        const correctAnswersHtml = `<h2>Correct Answers:</h2><p>${correctAnswersSection.replace("Correct Answers:", "").trim()}</p>`;
    
        // Combine the HTML elements into a single string, preserving the order
        const modalBodyHtml = `${otherHtml}${studentAnswersHtml}${correctAnswersHtml}`;
    
        // Set the modal body content
        modalBody.innerHTML = modalBodyHtml;
    
        // Add transition classes for fade-in
        resultModal.classList.remove('hidden');
        document.getElementById('modalOverlay').classList.replace('opacity-0', 'opacity-75');
        document.getElementById('modalContent').classList.replace('opacity-0', 'opacity-100');
    }
    
    closeModalBtn.addEventListener('click', function() {
        // Add transition classes for fade-out
        document.getElementById('modalOverlay').classList.replace('opacity-75', 'opacity-0');
        document.getElementById('modalContent').classList.replace('opacity-100', 'opacity-0');
    
        // Wait for the transition to complete before hiding the modal
        setTimeout(() => {
            resultModal.classList.add('hidden');
        }, 500);  // Match the duration of the fade-out transition
    });
});
