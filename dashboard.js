// static/dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const elements = {
        sessionListBody: document.getElementById('session-list-body'),
        fileListContainer: document.getElementById('file-list-container'),
        fileSearchInput: document.getElementById('file-search-input'),
        connectionStatusDot: document.querySelector('#connection-status .status-dot'),
        deviceCountSpan: document.getElementById('device-count'),
        modal: document.getElementById('details-modal'),
        modalTitle: document.getElementById('modal-title'),
        modalContent: document.getElementById('modal-content'),
        modalCloseBtn: document.getElementById('modal-close-btn'),
    };

    // --- Socket.IO Setup ---
    const socket = io();

    socket.on('connect', () => {
        console.log('Dashboard connected to server.');
        elements.connectionStatusDot.classList.remove('status-inactive');
        elements.connectionStatusDot.classList.add('status-active');
    });

    socket.on('disconnect', () => {
        console.warn('Dashboard disconnected.');
        elements.connectionStatusDot.classList.remove('status-active');
        elements.connectionStatusDot.classList.add('status-inactive');
    });
    
    // Listen for updates to connected devices
    socket.on('update_connected_devices', (data) => {
        const count = data.devices ? data.devices.length : 0;
        elements.deviceCountSpan.textContent = `${count} Device${count !== 1 ? 's' : ''} Connected`;
    });

    // Listen for events that require reloading the session list
    socket.on('sessions_updated', () => {
        console.log('Session list updated event received. Reloading sessions.');
        fetchActiveSessions();
    });

    // --- Data Fetching and Rendering ---

    async function fetchActiveSessions() {
        try {
            const response = await fetch('/get_active_sessions');
            const sessions = await response.json();
            renderActiveSessions(sessions);
        } catch (error) {
            console.error('Failed to fetch active sessions:', error);
            elements.sessionListBody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-red-500">Error loading sessions.</td></tr>`;
        }
    }

    function renderActiveSessions(sessions) {
        elements.sessionListBody.innerHTML = '';
        if (sessions.length === 0) {
            elements.sessionListBody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-muted">No active sessions found.</td></tr>`;
            return;
        }

        sessions.forEach(session => {
            const isWaiting = session.student === "Waiting for student...";
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="p-4"><div class="flex items-center"><div class="status-dot ${isWaiting ? 'status-prepared' : 'status-active'} mr-2"></div>${isWaiting ? 'Prepared' : 'In-Progress'}</div></td>
                <td class="p-4 font-mono">${session.exam_code}</td>
                <td class="p-4">${session.subject}</td>
                <td class="p-4">${session.student}</td>
                <td class="p-4 space-x-4">
                    <button class="action-btn text-blue-400 hover:text-blue-300" data-action="view-session" data-id="${session.id}" title="View Details"><i class="fas fa-eye"></i></button>
                    <button class="action-btn text-red-500 hover:text-red-400" data-action="terminate-session" data-id="${session.id}" title="Terminate Session"><i class="fas fa-trash-alt"></i></button>
                </td>
            `;
            elements.sessionListBody.appendChild(row);
        });
    }
    
    async function fetchAndRenderFiles() {
        try {
            const response = await fetch('/files');
            const fileData = await response.json();
            renderFiles(fileData);
        } catch (error) {
            console.error('Failed to fetch files:', error);
            elements.fileListContainer.innerHTML = `<p class="text-center text-red-500">Error loading files.</p>`;
        }
    }
    
    function renderFiles(fileData) {
        elements.fileListContainer.innerHTML = '';
        const allFiles = [];
        for (const subdir in fileData) {
            fileData[subdir].forEach(file => allFiles.push({ ...file, subdir }));
        }
        
        if (allFiles.length === 0) {
            elements.fileListContainer.innerHTML = `<p class="text-center text-muted">No files found on server.</p>`;
            return;
        }

        allFiles.forEach(file => {
            const fileRow = document.createElement('div');
            fileRow.className = 'flex items-center justify-between p-2 rounded-md hover:bg-secondary';
            fileRow.dataset.filename = file.filename.toLowerCase();
            
            fileRow.innerHTML = `
                <div class="flex items-center">
                    <i class="fas fa-file-alt text-accent mr-3"></i>
                    <span>${file.filename} <span class="text-sm text-muted">(${file.subdir})</span></span>
                </div>
                <div class="space-x-4">
                    <button class="action-btn text-blue-400" data-action="read-file" data-subdir="${file.subdir}" data-filename="${file.filename}" title="Read File"><i class="fas fa-book-open"></i></button>
                    <button class="action-btn text-green-400" data-action="broadcast-file" data-subdir="${file.subdir}" data-filename="${file.filename}" title="Broadcast to Clients"><i class="fas fa-bullhorn"></i></button>
                    <button class="action-btn text-red-500" data-action="delete-file" data-subdir="${file.subdir}" data-filename="${file.filename}" title="Delete File"><i class="fas fa-trash"></i></button>
                </div>
            `;
            elements.fileListContainer.appendChild(fileRow);
        });
    }

    // --- Event Delegation for Actions ---
    
    document.body.addEventListener('click', async (e) => {
        const button = e.target.closest('.action-btn');
        if (!button) return;

        const action = button.dataset.action;
        const id = button.dataset.id;
        const filename = button.dataset.filename;
        const subdir = button.dataset.subdir;

        if (action === 'terminate-session') {
            if (confirm(`Are you sure you want to terminate session ID ${id}? This action cannot be undone.`)) {
                socket.emit('terminate_session', { session_id: id });
            }
        }
        
        if (action === 'read-file') {
            try {
                const res = await fetch(`/read?subdirectory=${subdir}&filename=${filename}`);
                const data = await res.json();
                showModal('File Content: ' + filename, data.content || data.error);
            } catch (err) { showModal('Error', 'Could not read file.'); }
        }

        if (action === 'delete-file') {
            if (confirm(`Are you sure you want to delete "${filename}"?`)) {
                 try {
                    const res = await fetch('/delete', {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ subdirectory: subdir, filename: filename })
                    });
                    const data = await res.json();
                    if (data.error) throw new Error(data.error);
                    showModal('Success', data.message, true);
                    fetchAndRenderFiles(); // Refresh file list
                } catch (err) { showModal('Error', err.message); }
            }
        }

        if (action === 'broadcast-file') {
            if (confirm(`Broadcast "${filename}" to all connected clients?`)) {
                socket.emit('file_uploaded', { filename: filename, subdirectory: subdir });
                showModal('Broadcast Sent', `Notification for "${filename}" has been sent.`, true);
            }
        }
    });

    // --- Modal and Search ---

    elements.modalCloseBtn.addEventListener('click', () => elements.modal.classList.add('hidden'));

    elements.fileSearchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        document.querySelectorAll('#file-list-container > div').forEach(row => {
            const filename = row.dataset.filename;
            row.style.display = filename.includes(searchTerm) ? 'flex' : 'none';
        });
    });
    
    function showModal(title, content, autoClose = false) {
        elements.modalTitle.textContent = title;
        elements.modalContent.textContent = content;
        elements.modal.classList.remove('hidden');
        if (autoClose) {
            setTimeout(() => elements.modal.classList.add('hidden'), 2500);
        }
    }

    // --- Initial Load ---
    fetchActiveSessions();
    fetchAndRenderFiles();
});