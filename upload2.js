document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const fileContainer = document.getElementById('fileIconsContainer');
    const addNewBtn = document.getElementById('addNewBtn');
    const addNewModal = document.getElementById('addNewModal');
    const cancelBtn = document.getElementById('cancelBtn');
    const addNewForm = document.getElementById('addNewForm');
    const dialogueModal = document.getElementById('dialogueModal');
    const dialogueMessage = document.getElementById('dialogueMessage');
    const dialogueCloseBtn = document.getElementById('dialogueCloseBtn');
    const successModal = document.getElementById('successModal');

    // --- State ---
    let selectedFileIcon = null;

    // --- Initialize Socket.IO ---
    // The server will handle authentication via the session cookie.
    const socket = io();

    socket.on('connect', () => {
        console.log('Socket.IO connected successfully.');
    });

    socket.on('disconnect', () => {
        console.warn('Socket.IO disconnected.');
    });

    // --- Core Functions ---

    /**
     * Fetches files from the server and renders them as icons in the container.
     */
    async function fetchAndRenderFiles() {
        try {
            const response = await fetch('/files');
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            const data = await response.json();
            fileContainer.innerHTML = ''; // Clear existing icons

            if (Object.keys(data).length === 0) {
                fileContainer.innerHTML = `<p class="col-span-3 text-center text-gray-500">No files found. Click "Add New" to upload a file.</p>`;
                return;
            }

            for (const [subdirectory, fileList] of Object.entries(data)) {
                fileList.forEach(file => {
                    const fileIcon = createFileIcon(file.filename, subdirectory, file.source);
                    fileContainer.appendChild(fileIcon);
                });
            }
        } catch (error) {
            console.error('Error fetching files:', error);
            fileContainer.innerHTML = `<p class="col-span-3 text-center text-red-500">Error loading files. Please check the server connection.</p>`;
        }
    }

    /**
     * Creates a single file icon element with its dropdown menu.
     * @param {string} fileName - The name of the file.
     * @param {string} subdirectory - The subdirectory the file is in.
     * @param {string} source - Where the file is stored ('database' or 'filesystem').
     * @returns {HTMLElement} The file icon div element.
     */
    function createFileIcon(fileName, subdirectory, source) {
        const fileDiv = document.createElement('div');
        fileDiv.className = 'file-icon relative bg-slate-700 rounded-lg p-4 flex flex-col items-center justify-center h-32 w-32';
        fileDiv.dataset.filename = fileName;
        fileDiv.dataset.subdirectory = subdirectory;

        // Determine icon based on file type
        const extension = fileName.split('.').pop().toLowerCase();
        let iconClass = 'fa-file';
        if (['pdf'].includes(extension)) iconClass = 'fa-file-pdf';
        if (['doc', 'docx'].includes(extension)) iconClass = 'fa-file-word';
        if (['jpg', 'jpeg', 'png'].includes(extension)) iconClass = 'fa-file-image';

        fileDiv.innerHTML = `
            <i class="fas ${iconClass} text-5xl text-yellow-500"></i>
            <span class="absolute bottom-2 left-2 right-2 text-xs font-bold text-center truncate">${fileName}</span>
            <button class="dropdown-toggle absolute top-2 right-2 text-gray-400 hover:text-white">
                <i class="fas fa-ellipsis-v"></i>
            </button>
            <div class="dropdown hidden">
                <a href="#" class="dropdown-item" data-action="read">Read</a>
                <a href="#" class="dropdown-item" data-action="delete">Delete</a>
                <a href="#" class="dropdown-item" data-action="upload">Notify & Send</a>
            </div>
        `;

        // Event listener for the dropdown toggle button
        fileDiv.querySelector('.dropdown-toggle').addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent the main div click event
            const dropdown = fileDiv.querySelector('.dropdown');
            // Hide all other dropdowns before showing this one
            document.querySelectorAll('.dropdown.show').forEach(d => d.classList.remove('show'));
            dropdown.classList.toggle('show');
        });

        // Event listener for dropdown item clicks (event delegation)
        fileDiv.querySelector('.dropdown').addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (e.target.classList.contains('dropdown-item')) {
                const action = e.target.dataset.action;
                handleFileAction(action, fileName, subdirectory);
                fileDiv.querySelector('.dropdown').classList.remove('show');
            }
        });

        return fileDiv;
    }

    /**
     * Main handler that routes actions from dropdowns to the correct function.
     * @param {string} action - The action to perform ('read', 'delete', 'upload').
     * @param {string} fileName - The name of the file.
     * @param {string} subdirectory - The subdirectory of the file.
     */
    async function handleFileAction(action, fileName, subdirectory) {
        switch (action) {
            case 'read':
                try {
                    const response = await fetch(`/read?subdirectory=${subdirectory}&filename=${fileName}`);
                    const data = await response.json();
                    if (data.error) throw new Error(data.error);
                    showDialogue('File Content', `<pre class="whitespace-pre-wrap text-left">${data.content}</pre>`);
                } catch (error) {
                    showDialogue('Error', `Could not read file: ${error.message}`);
                }
                break;

            case 'delete':
                if (confirm(`Are you sure you want to delete "${fileName}"? This cannot be undone.`)) {
                    try {
                        const response = await fetch('/delete', {
                            method: 'DELETE',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ subdirectory, filename: fileName })
                        });
                        const data = await response.json();
                        if (data.error) throw new Error(data.error);
                        showDialogue('Success', data.message);
                        fetchAndRenderFiles(); // Refresh the file list
                    } catch (error) {
                        showDialogue('Error', `Could not delete file: ${error.message}`);
                    }
                }
                break;

            case 'upload':
                 // This action simply notifies connected clients via Socket.IO
                 // The server's `/upload` endpoint is for NEW files from the admin's PC.
                 if (confirm(`Notify all connected devices about "${fileName}"?`)) {
                    socket.emit('file_uploaded', { filename: fileName, subdirectory: subdirectory });
                    showDialogue('Sent', `Notification for "${fileName}" has been sent to all clients.`);
                 }
                break;
        }
    }

    /**
     * Handles the form submission for adding a new file.
     */
    addNewForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const subdirectory = addNewForm.querySelector('input[name="subdirectory"]:checked')?.value;
        const file = document.getElementById('fileUpload').files[0];

        if (!subdirectory || !file) {
            showDialogue('Error', 'Please select a subdirectory and a file.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('subdirectory', subdirectory);
        // The server will use the file's own name, so 'fileName' input is not needed.

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
                // Note: 'credentials' is not needed unless you are handling cross-origin cookies.
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to upload file.');
            }
            
            addNewModal.classList.add('hidden');
            successModal.classList.remove('hidden');
            addNewForm.reset();
            fetchAndRenderFiles(); // Refresh the file list

            setTimeout(() => {
                successModal.classList.add('hidden');
            }, 2000);

        } catch (error) {
            showDialogue('Upload Error', error.message);
        }
    });

    // --- Modal and UI Helper Functions ---
    
    function showDialogue(title, message) {
        dialogueModal.querySelector('h2').textContent = title;
        dialogueMessage.innerHTML = message; // Use innerHTML to render <pre> tags correctly
        dialogueModal.classList.remove('hidden');
    }

    // Modal close buttons
    addNewBtn.addEventListener('click', () => addNewModal.classList.remove('hidden'));
    cancelBtn.addEventListener('click', () => addNewModal.classList.add('hidden'));
    dialogueCloseBtn.addEventListener('click', () => dialogueModal.classList.add('hidden'));
    successModal.querySelector('.close').addEventListener('click', () => successModal.classList.add('hidden'));

    // Hide dropdowns if clicking anywhere else on the page
    document.addEventListener('click', () => {
        document.querySelectorAll('.dropdown.show').forEach(d => d.classList.remove('show'));
    });

    // --- Initial Load ---
    fetchAndRenderFiles();
});