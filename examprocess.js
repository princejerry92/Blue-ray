// static/examprocess.js

document.addEventListener("DOMContentLoaded", async () => {
    // --- Element Selectors ---
    const elements = { // Encapsulate all elements in a single object for consistency
        welcomeMessage: document.getElementById("welcomeMessage"),
        subjectDisplay: document.getElementById("subjectDisplay"),
        questionContainer: document.getElementById("questionContainer"),
        optionCarousel: document.getElementById("optioncarousel"),
        modal: document.getElementById("modal"),
        modalTitle: document.getElementById("modalTitle"),
        modalMessage: document.getElementById("modalMessage"),
        modalClose: document.getElementById("modalClose"),
        toggleLayoutButton: document.getElementById("toggleLayout"),
        submitButton: document.getElementById("submitButton"),
        timerElement: document.getElementById("timer"),
        timerIcon: document.getElementById("timerIcon"),
        mainContainer: document.getElementById('mainContainer'),
        loader: document.querySelector(".loader"),
        nextButton: document.getElementById('nextButton'),
        prevButton: document.getElementById('prevButton')
    };

    // --- State Variables ---
    let studentAnswers = {};
    let timerInterval;
    let currentCarouselIndex = 0; // Moved here to be accessible by all functions
    const beepAudio = new Audio('/static/img/assets/message-13716.mp3');

    /**
     * Fetches exam data and initializes the page.
     */
    async function initializeExam() {
        if (elements.loader) elements.loader.style.display = 'block';
        try {
            const response = await fetch('/examcenter');
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            
            const { student_data, formatted_document, exam_time } = data;

            if (!student_data || !formatted_document || !exam_time) {
                throw new Error("Incomplete exam data received from server.");
            }

            if (elements.welcomeMessage) elements.welcomeMessage.textContent = `Welcome, ${student_data.name || "Student"}`;
            if (elements.subjectDisplay) elements.subjectDisplay.textContent = student_data.exam_subject || "General Exam";
            if (elements.questionContainer) elements.questionContainer.innerHTML = formatted_document;

            const totalSeconds = timeStringToSeconds(exam_time);
            startCountdownTimer(totalSeconds);
            
            const questionLength = parseInt(student_data.question_length, 10);
            createOptionCarousel(questionLength);
            
        } catch (error) {
            console.error("Failed to initialize exam:", error);
            showModal("Load Error", `Could not load exam data. Please try again. Error: ${error.message}`);
        } finally {
            if (elements.loader) elements.loader.style.display = 'none';
        }
    }

    function timeStringToSeconds(timeValue) {
        if (typeof timeValue === 'number') return timeValue;
        if (typeof timeValue === 'string') {
            const parts = timeValue.split(':').map(part => parseInt(part, 10));
            if (parts.length === 3 && !parts.some(isNaN)) {
                const [hours, minutes, seconds] = parts;
                return (hours * 3600) + (minutes * 60) + seconds;
            }
        }
        console.warn("Invalid time format received:", timeValue);
        return 0;
    }

    /**
     * Creates the multiple-choice option carousel.
     * @param {number} questionLength - The total number of questions.
     */
    function createOptionCarousel(questionLength) {
        if (!elements.optionCarousel) return;
        elements.optionCarousel.innerHTML = '';
        for (let i = 1; i <= questionLength; i++) {
            const qKey = `q${i}`;
            const item = document.createElement('div');
            item.className = 'carousel-item hidden';
            item.dataset.question = qKey;

            let optionsHTML = `<h3 class="text-xl font-semibold mb-4 text-blue-200">Question ${i}</h3><div class="space-y-3">`;
            ['A', 'B', 'C', 'D'].forEach(opt => {
                optionsHTML += `
                    <label class="flex items-center text-lg cursor-pointer p-2 rounded-md hover:bg-gray-700 transition-colors duration-200">
                        <input type="radio" name="${qKey}" value="${opt}" class="mr-3 form-radio h-5 w-5 text-blue-500 bg-gray-700 border-gray-600 focus:ring-blue-500">
                        <span>${opt}</span>
                    </label>
                `;
            });
            optionsHTML += '</div>';
            item.innerHTML = optionsHTML;

            // Add event listener for the entire option group
            item.addEventListener('change', (e) => {
                if (e.target.type === 'radio') {
                    studentAnswers[e.target.name] = e.target.value;
                    
                    // --- THE NEW LOGIC ---
                    // After a brief delay to show the selection, move to the next question.
                    setTimeout(() => showCarouselItem(currentCarouselIndex + 1), 250);
                }
            });

            elements.optionCarousel.appendChild(item);
        }
        showCarouselItem(0); // Show the first question
    }
    
    // --- Carousel Navigation ---
    function showCarouselItem(index) {
        const items = document.querySelectorAll('.carousel-item');
        // If we've answered the last question, don't try to go further.
        if (index >= items.length) {
            // Optional: You could focus the submit button here.
            elements.submitButton.focus();
            return;
        }
        if (index < 0) return; // Boundary check for previous button

        items.forEach((item, i) => {
            item.classList.toggle('hidden', i !== index);
        });
        currentCarouselIndex = index;
    }

    if (elements.nextButton) elements.nextButton.addEventListener('click', () => showCarouselItem(currentCarouselIndex + 1));
    if (elements.prevButton) elements.prevButton.addEventListener('click', () => showCarouselItem(currentCarouselIndex - 1));

    // --- Timer and Submission Logic (No changes needed here) ---
    
    function startCountdownTimer(durationInSeconds) {
        let remainingTime = durationInSeconds;
        clearInterval(timerInterval);

        timerInterval = setInterval(() => {
            if (remainingTime <= 0) {
                clearInterval(timerInterval);
                if (elements.timerElement) elements.timerElement.textContent = "00:00:00";
                showModal("Time's Up!", "Your exam is being submitted automatically.");
                setTimeout(forceSubmitExam, 2000);
                return;
            }
            remainingTime--;
            const hours = String(Math.floor(remainingTime / 3600)).padStart(2, '0');
            const minutes = String(Math.floor((remainingTime % 3600) / 60)).padStart(2, '0');
            const seconds = String(remainingTime % 60).padStart(2, '0');
            if (elements.timerElement) elements.timerElement.textContent = `${hours}:${minutes}:${seconds}`;

            if (remainingTime === 300) {
                if (elements.timerElement) elements.timerElement.style.color = "#f56565";
                playBeep();
            } else if (remainingTime === 60) {
                if (elements.timerElement) elements.timerElement.classList.add("pulse");
            } else if (remainingTime <= 10 && remainingTime > 0) {
                playBeep();
            }
        }, 1000);
    }
    
    function forceSubmitExam() {
        sendAnswers(true);
    }

    async function sendAnswers(isForced = false) {
        clearInterval(timerInterval);
        try {
            const response = await fetch('/mark', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(studentAnswers)
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to submit answers.');
            }
            showModal("Success", "Exam submitted successfully! Preparing your results...");
            setTimeout(() => {
                window.location.href = '/scoreboard';
            }, 3000);
        } catch (error) {
            console.error("Submission Error:", error);
            showModal("Submission Error", "Could not submit your answers. Please check your connection.");
        }
    }
    
    // --- UI and Modal Handlers (No changes needed here) ---

    function playBeep() {
        beepAudio.play().catch(e => console.error("Audio playback error:", e));
    }

    function showModal(title, message) {
        if (!elements.modal || !elements.modalTitle || !elements.modalMessage) return;
        elements.modalTitle.textContent = title;
        elements.modalMessage.innerHTML = message;
        elements.modal.classList.remove("hidden");
        playBeep();
    }
    
    if (elements.modalClose) {
        elements.modalClose.addEventListener("click", () => elements.modal.classList.add("hidden"));
    }

    // Add CSS class for unanswered question highlight
    const style = document.createElement('style');
    style.innerHTML = `
        .unanswered-highlight {
            border: 2px solid red !important;
            border-radius: 8px;
        }
    `;
    document.head.appendChild(style);

    // Helper function to clear all unanswered highlights
    function clearUnansweredHighlights() {
        const items = document.querySelectorAll('.carousel-item.unanswered-highlight');
        items.forEach(item => item.classList.remove('unanswered-highlight'));
    }

    // Helper function to highlight unanswered questions
    function highlightUnansweredQuestions(unansweredQuestions) {
        clearUnansweredHighlights();
        unansweredQuestions.forEach(qKey => {
            const item = document.querySelector(`.carousel-item[data-question="${qKey}"]`);
            if (item) {
                item.classList.add('unanswered-highlight');
            }
        });
    }

    // Remove highlight when a question is answered
    function removeHighlightOnAnswer() {
        const items = document.querySelectorAll('.carousel-item');
        items.forEach(item => {
            item.addEventListener('change', (e) => {
                if (e.target.type === 'radio') {
                    item.classList.remove('unanswered-highlight');
                }
            });
        });
    }

    // Remove highlight when navigating questions
    function removeHighlightOnNavigation() {
        if (elements.nextButton) {
            elements.nextButton.addEventListener('click', () => {
                clearUnansweredHighlights();
            });
        }
        if (elements.prevButton) {
            elements.prevButton.addEventListener('click', () => {
                clearUnansweredHighlights();
            });
        }
    }

    // Clear highlights when modal is closed
    if (elements.modalClose) {
        elements.modalClose.addEventListener('click', () => {
            elements.modal.classList.add("hidden");
            clearUnansweredHighlights();
        });
    }

    if (elements.submitButton) {
        elements.submitButton.addEventListener('click', () => {
            const questionLength = document.querySelectorAll('.carousel-item').length;
            const unansweredQuestions = [];
            for (let i = 1; i <= questionLength; i++) {
                const qKey = `q${i}`;
                if (!(qKey in studentAnswers)) {
                    unansweredQuestions.push(qKey);
                }
            }
            if (unansweredQuestions.length > 0) {
                // Show modal with list of unanswered questions
                const questionListHTML = unansweredQuestions.map(q => `<li>Question ${q.substring(1)}</li>`).join('');
                showModal("Incomplete Exam", `<p>Please answer all questions before submitting. Unanswered questions:</p><ul style="text-align:left; color:#f87171; margin-top:10px;">${questionListHTML}</ul>`);
                highlightUnansweredQuestions(unansweredQuestions);
            } else {
                showModal("Confirm Submission", `<p>Are you sure you want to submit your exam?</p>
                    <div class="flex justify-center gap-4 mt-4">
                        <button id="confirmSubmit" class="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-6 rounded-full">Yes, Submit</button>
                        <button id="cancelSubmit" class="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-6 rounded-full">Cancel</button>
                    </div>`);
                
                const confirmSubmitBtn = document.getElementById('confirmSubmit');
                const cancelSubmitBtn = document.getElementById('cancelSubmit');

                if (confirmSubmitBtn) confirmSubmitBtn.onclick = () => {
                    elements.modal.classList.add("hidden");
                    sendAnswers();
                };
                if (cancelSubmitBtn) cancelSubmitBtn.onclick = () => elements.modal.classList.add("hidden");
            }
        });
    }

    // Initialize highlight removal listeners
    removeHighlightOnAnswer();
    removeHighlightOnNavigation();

    if (elements.toggleLayoutButton) {
        elements.toggleLayoutButton.addEventListener('click', () => {
            if (elements.mainContainer) elements.mainContainer.classList.toggle('column-layout');
        });
    }

    window.onbeforeunload = () => "Are you sure you want to leave? Your exam progress will be lost.";

    // --- Start the Application ---
    initializeExam();
});