let globalIpAddress = '';
let socket;
let downloadCount = 0;


document.addEventListener('DOMContentLoaded', function() {
    // DOM element references
    const elements = {
        fileIcons: document.querySelectorAll('.file-icon'),
        dropdown: document.getElementById('dropdown'),
        listModal: document.getElementById('listModal'),
        errorModal: document.getElementById('errorModal'),
        fileList: document.getElementById('fileList'),
        downloadAnimation: document.getElementById('downloadAnimation'),
        ipInput: document.getElementById('ipInput'),
        closeButtons: document.querySelectorAll('.close'),
        resultUploader: document.getElementById('resultUploader'),
        fileInput: document.getElementById('fileInput'),
        connectionModal: document.getElementById('connectionModal'),
        progressModal: document.getElementById('progress-modal'),
        resultModal: document.getElementById('resultModal'),
        emitEventIcon: document.getElementById('emitEventIcon'),
        updateProgress: document.getElementById('progressStatus'),
        badge: document.getElementById('badge') // Add the badge to the elements object

    };

    let selectedIcon = null;

    // Event listeners
    elements.ipInput.addEventListener('change', handleIpChange);
    elements.resultUploader.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', handleFileUpload);
    document.getElementById('listBtn').addEventListener('click', listFiles);
    document.getElementById('downloadBtn').addEventListener('click', handleDownloadClick);

    elements.fileIcons.forEach(icon => icon.addEventListener('click', handleIconClick));
    document.addEventListener('click', handleOutsideClick);
    elements.closeButtons.forEach(button => button.addEventListener('click', closeModal));
    window.addEventListener('click', closeModalOnOutsideClick);

    // Socket connection function
    function connectToSocket() {
        if (globalIpAddress) {
            if (socket) socket.disconnect();
            
            socket = io(`http://${globalIpAddress}`, {
                transports: ['websocket'],
                reconnectionAttempts: 5,
                credentials: 'include',
                reconnectionDelay: 6000
            });

            socket.on('connect', () => {
                console.log('Connected to admin server');
                showModal(elements.connectionModal, 'Connected to Admin Server', '<div class="text-green-500 text-3xl">&#9889;</div><span class="text-white">Connected to Admin Server</span>');
                showEmitIcon();
            });

            socket.on('upload_progress_ack', (data) => {
                console.log(`Received upload progress acknowledgement: ${data.filename} - ${data.progress}%`);
                updateProgress(data.progress);
            });

            socket.on('disconnect', () => {
                console.log('Disconnected from admin server');
                showModal(elements.connectionModal, 'Disconnected from Admin Server', '<div class="text-white">❌</div><span class="text-white">Disconnected from Admin Server</span>');
            });

        }
            // Update badge count when a file is received
            socket.on('file_received', function (data) {
                console.log('File received:', data);
                downloadCount++;
                console.log('Download count incremented:', downloadCount);
                updateBadge(downloadCount);
                
                // Play beep sound
                new Audio('../static/img/assets/message-13716.mp3').play();
                console.log('Beep sound played');
            });
            
    }
    

    // Event handlers
    function handleIpChange() {
        globalIpAddress = this.value;
        console.log("IP Address updated:", globalIpAddress);
        connectToSocket();
    }

    function handleIconClick(e) {
        if (selectedIcon) selectedIcon.classList.remove('selected');
        this.classList.add('selected');
        selectedIcon = this;

        elements.dropdown.style.display = 'block';
        elements.dropdown.style.left = `${e.pageX}px`;
        elements.dropdown.style.top = `${e.pageY}px`;
    }

    function handleOutsideClick(e) {
        if (!e.target.closest('.file-icon') && !e.target.closest('#dropdown')) {
            elements.dropdown.style.display = 'none';
            if (selectedIcon) {
                selectedIcon.classList.remove('selected');
                selectedIcon = null;
            }
        }
    }
    
    function handleDownloadClick() {
        if (selectedIcon) {
            const filename = selectedIcon.querySelector('img').alt;
            downloadFile(filename);
        } else {
            showError('Download Error', 'Please select a file icon first.');
        }
    }

    function handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!globalIpAddress) {
            showError('Error', 'Please enter a host IP address.');
            return;
        }

        if (!socket) {
            showError('Error', 'Not connected to the server.');
            return;
        }
        showProgressModal();
        updateProgress(0);

        const reader = new FileReader();
        reader.onload = function (e) {
            const filedata = e.target.result.split(',')[1];
            socket.emit('upload_file_to_admin', {
                filename: file.name,
                credentials: 'include',
                filedata: filedata
            });
             // Simulate progress updates (replace this with actual progress if available)
             let progress = 0;
             const progressInterval = setInterval(() => {
                 progress += 10;
                 if (progress > 100) {
                     clearInterval(progressInterval);
                     return;
                 }
                 socket.emit('upload_progress', {
                     filename: file.name,
                     progress: progress
                 });
             }, 500);
         };
           
        reader.onerror = function (e) {
            console.error('Error reading file:', e);
            showError('Error', 'Failed to read file.');
        };

        reader.readAsDataURL(file);
    }

    function handleFileReceived(data) {
        showEmitIcon();
        if (data.error) {
            showError('Error', data.error);
        } else {
            console.log('File received:', data.message);
            showModal(elements.resultModal, "File Upload Success", "<div class=\"text-green-500 text-3xl\">&#10004;</div><span>File recieved</span>");
            updateBadge(downloadCount);
            downloadCount++;

 
            }
            hideProgressModal();
    }

    // Utility functions
    async function listFiles() {
        if (!globalIpAddress) {
            showError('Error', 'Please enter a host IP address.');
            return;
        }
    
        try {
            const response = await fetch(`http://${globalIpAddress}/list_files`);
            if (!response.ok) throw new Error('Failed to fetch file list');
            
            const data = await response.json();
            elements.fileList.innerHTML = '';
    
            if (data.files.length === 0) {
                elements.fileList.innerHTML = '<li>No files available for download</li>';
            } else {
                data.files.forEach(file => {
                    const li = document.createElement('li');
                    const link = document.createElement('a');
                    link.textContent = file.filename;
                    link.href = `http://${globalIpAddress}${file.download_url}`;
                    link.target = '_blank';  // Opens the download in a new tab
                    
                    li.appendChild(link);
                    elements.fileList.appendChild(li);
                });
            }
    
            elements.listModal.style.display = 'block';
        } catch (error) {
            showError('Error', error.message);
            console.error('Error fetching file list:', error);
        }
    }
    
    
    async function downloadFile(filename) {
        if (!globalIpAddress) {
            showError('Error', 'Please enter a host IP address.');
            return;
        }
    
        // Extract subdirectory from filename if applicable
        const parts = filename.split('/');
        const subdirectory = parts.length > 1 ? parts.slice(0, -1).join('/') : ''; // Gets subdirectory
        const actualFilename = parts[parts.length - 1]; // Gets actual filename
    
        elements.downloadAnimation.style.display = 'block';
    
        try {
            const response = await fetch(`http://${globalIpAddress}/download1`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: actualFilename, subdirectory }),
            });
    
            if (!response.ok) throw new Error(`Download failed: ${response.statusText}`);
    
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
    
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = actualFilename;
            document.body.appendChild(a);
            a.click();
    
            window.URL.revokeObjectURL(url);
        } catch (error) {
            showError('Download Error', error.message);
            console.error('Error downloading file:', error);
        } finally {
            elements.downloadAnimation.style.display = 'none';
        }
    }    
    
    function showError(title, message) {
        console.log("Showing error:", title, message);
        document.getElementById('errorTitle').textContent = title;
        document.getElementById('errorMessage').textContent = message;
        elements.errorModal.style.display = 'block';
    }

    function showModal(modal, title = '', icon = '') {
        console.log("Showing modal:", modal.id, title);
        if (title) {
            const titleElement = modal.querySelector('h2');
            titleElement.textContent = title;
            titleElement.style.fontWeight = 'bold';
            titleElement.style.fontSize = '24px';
            titleElement.style.color = '#333';
        }
        if (icon) modal.querySelector('div').innerHTML = icon;
        modal.style.display = 'block';
    }

    function closeModal() {
        this.closest('.modal').style.display = 'none';
    }

    function closeModalOnOutsideClick(e) {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    }

    function updateProgress(progress) {
        console.log("Updating progress:", progress);
        const progressStatus = document.getElementById('progressStatus');
        const progressBar = document.querySelector('#progress-modal .bg-green-500');
        const progressPercentage = document.getElementById('progressPercentage');
        progressStatus.textContent = `Sending... ${progress}%`;

        // Update the progress bar width
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
    
        // Update the percentage text
        if (progressPercentage) {
            progressPercentage.textContent = `${progress}%`;
        }
    }
    function showProgressModal() {
        const progressModal = document.getElementById('progress-modal');
        if (progressModal) {
            progressModal.style.display = 'block';
        } else {
            console.error("Progress modal element not found.");
        }
    }
    function hideProgressModal() {
        const progressModal = document.getElementById('progress-modal');
        if (progressModal) {
            progressModal.style.display = 'none';
        }
    }

    function showEmitIcon() {
        elements.emitEventIcon.style.display = 'inline-block';
        elements.emitEventIcon.textContent = 'Event emitted!'; // add text content
        elements.emitEventIcon.title = 'Event emitted successfully'; // add title attribute
        setTimeout(() => {
            elements.emitEventIcon.style.display = 'none';
        }, 2000);
    }
   
    
    // Function to update badge with file count
    function updateBadge(count) {
        console.log('Updating badge with count:', count);
        const badge = document.getElementById('badge');
        
        if (count > 0) {
            badge.style.display = 'inline'; // Make the badge visible
            badge.textContent = count;
        } else {
            badge.style.display = 'none'; // Hide the badge if count is zero
        }
        
        console.log('Badge text content set to:', count);
    }


    // Open modal to display downloaded files
    document.getElementById('Downloads').addEventListener('click', function () {
        console.log('Downloads button clicked');
        fetch('/files')
            .then(response => response.json())
            .then(data => {
                console.log('Fetched files:', data);
                const fileList = document.getElementById('fileList');
                fileList.innerHTML = '';  // Clear previous entries
        
                data.files.forEach(file => {
                    const listItem = document.createElement('li');
                    listItem.textContent = file;
                    fileList.appendChild(listItem);
                });
        
                // Show modal
                document.getElementById('listModal').style.display = 'block';
                console.log('Modal displayed');
            })
            .catch(error => {
                console.error('Error fetching files:', error);
            });
    });

    // Close modal
    document.querySelectorAll('.close').forEach(function (closeButton) {
        closeButton.addEventListener('click', function () {
            closeButton.closest('.modal').style.display = 'none';
            console.log('Modal closed');
        });
    });

    // Fetch and display download files on modal opening
    document.getElementById('Downloads').addEventListener('click', function () {
        console.log('Downloads button clicked to fetch files');
        fetchFiles();
    });

    // Fetch the list of downloaded files
    function fetchFiles() {
        console.log('Fetching files...');
        fetch('/files')
            .then(response => response.json())
            .then(data => {
                console.log('Fetched files:', data);
                const fileList = document.getElementById('fileList');
                fileList.innerHTML = '';  // Clear the list
        
                // Populate the list with files
                data.files.forEach(file => {
                    const listItem = document.createElement('li');
                    listItem.textContent = file;
                    fileList.appendChild(listItem);
                });
        
                // Show the modal with files
                document.getElementById('listModal').style.display = 'block';
                console.log('Modal displayed with files');
            })
            .catch(error => {
                console.error('Error fetching files:', error);
            });
    }
    });