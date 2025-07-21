// static/result_portal.js

document.addEventListener("DOMContentLoaded", () => {
    // --- Element Selectors ---
    const elements = {
        socketIndicator: document.getElementById('socketioConnect'),
        messageArea: document.getElementById('messageArea'),
        resultsTableBody: document.getElementById('resultsTableBody'),
        envelopeIcon: document.getElementById('envelope'),
        bellIcon: document.getElementById('Vibratingbell'),
        
        // Login Modal
        loginModal: document.getElementById('adminLoginModal'),
        loginButton: document.getElementById('loginButton'), // The button in the header
        adminLoginButton: document.getElementById('adminLoginButton'), // The button inside the modal
        adminUsernameInput: document.getElementById('adminUsername'),
        adminPasswordInput: document.getElementById('adminPassword'),

        // Result Viewing Modal
        resultModal: document.getElementById('resultModal'),
        resultModalTitle: document.querySelector('#resultModal #modalTitle'),
        resultModalBody: document.querySelector('#resultModal #modalBody'),
        closeResultModalBtn: document.querySelector('#resultModal #closeModalBtn'),

        // Printing
        printButton: document.getElementById('printResultsButton'),
        selectAllButton: document.getElementById('selectAll'),
        printFontSizeOptions: document.querySelectorAll('[data-font-size]'),
    };

    // --- State ---
    let adminToken = null; // We get this from login to authenticate the socket connection
    let newResultsCount = 0;

    // --- Initialize Socket.IO ---
    const socket = io(); // Automatically connects to the server that served the page

    // =========================================================================
    // 1. AUTHENTICATION & SOCKET.IO FLOW
    // =========================================================================

    // Show the login modal immediately on page load
    if (elements.loginModal) {
        elements.loginModal.classList.remove('hidden');
    }

    socket.on('connect', () => {
        console.log('Socket.IO connected.');
        if (elements.socketIndicator) {
            elements.socketIndicator.style.color = 'green';
        }
        displayMessage('Connected to server. Please log in as an admin to receive results.', 'info');
        // If we have a token from a previous login, try to authenticate
        if (adminToken) {
            authenticateSocket();
        }
    });

    socket.on('disconnect', () => {
        console.warn('Socket.IO disconnected.');
        if (elements.socketIndicator) {
            elements.socketIndicator.style.color = 'brown';
        }
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

    /**
     * Handles the HTTP login process.
     */
    async function handleAdminLogin() {
        const username = elements.adminUsernameInput.value;
        const password = elements.adminPasswordInput.value;

        try {
            const response = await fetch('/portal_admin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });
            const data = await response.json();

            if (!response.ok || !data.token) {
                throw new Error(data.error || 'Invalid credentials.');
            }

            // --- Success ---
            adminToken = data.token; // Store the token
            displayMessage('Login successful! Authenticating real-time session...', 'success');
            if (elements.loginModal) {
                elements.loginModal.classList.add('hidden');
            }
            authenticateSocket(); // Now authenticate the socket with the token

        } catch (error) {
            console.error('Login failed:', error);
            displayMessage(`Login failed: ${error.message}`, 'error');
        }
    }

    /**
     * Emits an event to the server to associate this socket connection with the logged-in admin.
     */
    function authenticateSocket() {
        if (!socket.connected) {
            displayMessage('Cannot authenticate. Not connected to the server.', 'error');
            return;
        }
        socket.emit('authenticate_admin', { token: adminToken });
        displayMessage('Session authenticated. Ready to receive results.', 'success');
    }

    // --- Event Listeners for Authentication ---
    if (elements.adminLoginButton) {
        elements.adminLoginButton.addEventListener('click', handleAdminLogin);
    }
    if (elements.loginButton) {
        elements.loginButton.addEventListener('click', () => {
            if (elements.loginModal) {
                elements.loginModal.classList.remove('hidden');
            }
        });
    }

    // =========================================================================
    // 2. DYNAMIC TABLE & UI UPDATES
    // =========================================================================

    /**
     * Adds a new row to the results table.
     * @param {string} filename - The name of the result file received.
     */
    function addResultRow(filename) {
        if (!elements.resultsTableBody) return;

        const now = new Date();
        const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const date = now.toLocaleDateString();

        const row = document.createElement('tr');
        row.dataset.filename = filename; // Store filename in row dataset for printing
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-no-wrap border-b border-gray-200">
                <div class="text-sm leading-5 text-gray-100">STUDENT-DEVICE</div>
                <i class="fi fi-ss-computer inline"></i>
            </td>
            <td class="px-6 py-4 whitespace-no-wrap border-b border-gray-200">
                <div class="text-sm leading-5 font-medium text-gray-100">${filename}</div>
            </td>
            <td class="px-6 py-4 whitespace-no-wrap border-b border-gray-200 text-sm leading-5 text-gray-100">${time}</td>
            <td class="px-6 py-4 whitespace-no-wrap border-b border-gray-200 text-sm leading-5 text-gray-100">${date}</td>
            <td class="px-6 py-4 whitespace-no-wrap border-b border-gray-200 text-sm leading-5 font-medium">
                <button class="view-result-btn text-indigo-600 hover:text-indigo-900" data-filename="${filename}">
                    <i class="far fa-eye"></i> View
                </button>
            </td>
            <td class="px-6 py-4 whitespace-no-wrap border-b border-gray-200">
               <input type="checkbox" class="result-checkbox rounded border-gray-300 text-teal-600 focus:ring-teal-600">
            </td>
        `;
        // Prepend the new row to the top of the table for visibility
        elements.resultsTableBody.prepend(row);
    }

    /**
     * Handles clicks on the "View" button in the table.
     */
    if (elements.resultsTableBody) {
        elements.resultsTableBody.addEventListener('click', async (event) => {
            const viewButton = event.target.closest('.view-result-btn');
            if (viewButton) {
                const filename = viewButton.dataset.filename;
                try {
                    const response = await fetch(`/view_result?filename=${encodeURIComponent(filename)}`);
                    const data = await response.json();
                    if (data.error) throw new Error(data.error);

                    if (elements.resultModalTitle && elements.resultModalBody) {
                        elements.resultModalTitle.textContent = `Result: ${data.filename}`;
                        // Use a <pre> tag to preserve formatting (line breaks, spaces)
                        elements.resultModalBody.innerHTML = `<pre class="whitespace-pre-wrap text-xs">${data.content}</pre>`;
                    }
                    if (elements.resultModal) {
                        elements.resultModal.classList.remove('hidden');
                    }
                } catch (error) {
                    displayMessage(`Error viewing result: ${error.message}`, 'error');
                }
            }
        });
    }

    if (elements.closeResultModalBtn && elements.resultModal) {
        elements.closeResultModalBtn.addEventListener('click', () => {
            elements.resultModal.classList.add('hidden');
        });
    }

    // --- UI Helpers ---
    function displayMessage(message, type = 'info') {
        if (!elements.messageArea) return;
        
        elements.messageArea.textContent = message;
        elements.messageArea.className = 'mt-4 p-4 rounded-lg'; // Reset classes
        if (type === 'success') {
            elements.messageArea.classList.add('bg-green-100', 'text-green-700');
        } else if (type === 'error') {
            elements.messageArea.classList.add('bg-red-100', 'text-red-700');
        } else {
            elements.messageArea.classList.add('bg-blue-100', 'text-blue-700');
        }
    }

    function playNotificationSound() {
        if (!elements.bellIcon) return;
        
        const beep = new Audio('../static/img/assets/message-13716.mp3');
        beep.play().catch(e => console.error("Audio playback error:", e));
        elements.bellIcon.classList.add('animate-ping');
        setTimeout(() => {
            if (elements.bellIcon) {
                elements.bellIcon.classList.remove('animate-ping');
            }
        }, 3000);
    }

    function updateNotificationBadge(count) {
        if (!elements.envelopeIcon) return;
        
        let badge = elements.envelopeIcon.querySelector('.badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'badge absolute top-2 right-2 bg-red-500 text-white rounded-full h-5 w-5 flex items-center justify-center text-xs';
            elements.envelopeIcon.appendChild(badge);
        }
        badge.textContent = count;
    }

    // =========================================================================
    // 3. PRINTING LOGIC
    // =========================================================================
    let selectedFontSize = '12px'; // Default font size

    if (elements.printFontSizeOptions) {
        elements.printFontSizeOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                selectedFontSize = e.target.dataset.fontSize === 'large' ? '18px' : '12px';
                displayMessage(`Print font size set to ${e.target.dataset.fontSize}.`, 'info');
            });
        });
    }

    if (elements.selectAllButton) {
        elements.selectAllButton.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.result-checkbox').forEach(cb => cb.checked = true);
        });
    }

    if (elements.printButton) {
        elements.printButton.addEventListener('click', async () => {
            const selectedCheckboxes = document.querySelectorAll('.result-checkbox:checked');
            if (selectedCheckboxes.length === 0) {
                displayMessage('Please select at least one result to print.', 'error');
                return;
            }

            displayMessage(`Preparing ${selectedCheckboxes.length} result(s) for printing...`, 'info');
            
            let combinedPrintContent = '';
            
            // Use Promise.all to fetch all selected results concurrently for better performance
            const fetchPromises = Array.from(selectedCheckboxes).map(checkbox => {
                const row = checkbox.closest('tr');
                const filename = row.dataset.filename;
                return fetch(`/view_result?filename=${encodeURIComponent(filename)}`)
                    .then(response => {
                        if (!response.ok) return { error: `Failed to fetch ${filename}` };
                        return response.json();
                    });
            });

            try {
                const results = await Promise.all(fetchPromises);

                for (const data of results) {
                    if (data.error || !data.content) {
                        console.warn(`Skipping a file due to error:`, data.error || 'No content');
                        continue; // Skip failed fetches or empty content
                    }
                    
                    // Sanitize content to prevent HTML injection before inserting into the page
                    const sanitizedContent = data.content.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                    
                    combinedPrintContent += `
                        <div class="page-break">
                            <h2>Result: ${data.filename}</h2>
                            <pre>${sanitizedContent}</pre>
                        </div>
                    `;
                }
            } catch (error) {
                console.error("Error fetching print data:", error);
                displayMessage('An error occurred while preparing files for printing.', 'error');
                return;
            }

            if (combinedPrintContent) {
                // --- Modern and Reliable Printing Method ---
                const printWindow = window.open('', '_blank');
                if (!printWindow) {
                    displayMessage('Please allow pop-ups for this site to print results.', 'error');
                    return;
                }

                // Create the full HTML document for the new window
                const printHtml = `
                    <html>
                        <head>
                            <title>Print Results</title>
                            <style>
                                body { 
                                    font-family: 'Courier New', Courier, monospace; 
                                    font-size: ${selectedFontSize}; 
                                    margin: 20px;
                                }
                                .page-break { 
                                    page-break-after: always; 
                                    border: 1px solid #eee; 
                                    padding: 15px; 
                                    margin-bottom: 20px;
                                }
                                h2 { 
                                    border-bottom: 2px solid #333; 
                                    padding-bottom: 5px; 
                                    font-family: Arial, sans-serif;
                                }
                                pre { 
                                    white-space: pre-wrap; 
                                    word-wrap: break-word; 
                                }
                                @media print {
                                    .page-break {
                                        border: none;
                                    }
                                }
                            </style>
                        </head>
                        <body>
                            ${combinedPrintContent}
                        </body>
                    </html>
                `;
                
                // Write the HTML to the new window's document
                printWindow.document.open();
                printWindow.document.write(printHtml);
                printWindow.document.close(); // Important: Finalizes the document loading

                // Wait for the content to be fully parsed before printing
                printWindow.onload = function() {
                    printWindow.focus();  // Focus the new window
                    printWindow.print();  // Open the print dialog
                    // printWindow.close(); // Optional: close the window after printing
                };
                
            } else {
                displayMessage('Could not prepare any selected files for printing.', 'error');
            }
        });
    }
});