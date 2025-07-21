// static/connections.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const elements = {
        hostName: document.getElementById('hostName'),
        hostIp: document.getElementById('hostIp'),
        scanBtn: document.getElementById('scanBtn'),
        originsBtn: document.getElementById('originsBtn'),
        originsDropdown: document.getElementById('originsDropdown'),
        addOriginBtn: document.getElementById('addOriginBtn'),
        deleteOriginBtn: document.getElementById('deleteOriginBtn'),
        connectedDevicesContainer: document.getElementById('connectedDevices'),
        addOriginModal: document.getElementById('addOriginModal'),
        deleteOriginModal: document.getElementById('deleteOriginModal'),
        addOriginInput: document.getElementById('addOriginInput'),
        deleteOriginInput: document.getElementById('deleteOriginInput'),
        submitAddOriginBtn: document.getElementById('submitAddOrigin'),
        submitDeleteOriginBtn: document.getElementById('submitDeleteOrigin'),
        addOriginMessage: document.getElementById('addOriginMessage'),
        deleteOriginMessage: document.getElementById('deleteOriginMessage'),
    };

    // --- Initialize Socket.IO ---
    const socket = io();

    // --- Socket.IO Event Handlers for Real-Time Updates ---
    socket.on('connect', () => {
        console.log('Connected to the server. Ready for real-time updates.');
        // Request initial data upon connection
        fetchHostInfo();
        socket.emit('get_initial_devices'); // We'll create this server-side event
    });

    socket.on('update_connected_devices', (data) => {
        console.log('Received device update:', data);
        renderConnectedDevices(data.devices || []);
    });

    // --- Core Functions ---

    /**
     * Fetches the host's IP and name from the server.
     */
    async function fetchHostInfo() {
        try {
            const response = await fetch('/get_host_ip');
            const data = await response.json();
            if (data.host_name) elements.hostName.innerText = data.host_name;
            if (data.host_ip) elements.hostIp.innerText = `Host IP: ${data.host_ip}`;
        } catch (error) {
            console.error('Error fetching host info:', error);
            elements.hostName.innerText = 'Error';
            elements.hostIp.innerText = 'Could not fetch host IP.';
        }
    }

    /**
     * Renders the list of connected devices in the UI.
     * This function is now called by the real-time 'update_connected_devices' event.
     * @param {Array} devices - An array of device objects.
     */
    function renderConnectedDevices(devices) {
        elements.connectedDevicesContainer.innerHTML = ''; // Clear previous list
        if (devices.length === 0) {
            elements.connectedDevicesContainer.innerHTML = '<p class="text-center text-gray-400">No devices connected.</p>';
            return;
        }

        devices.forEach(device => {
            const iconClass = device.role === 'admin' ? 'fa-user-shield' : 'fa-mobile-alt';
            const roleColor = device.role === 'admin' ? 'text-green-400' : 'text-blue-400';
            
            const deviceElement = document.createElement('div');
            deviceElement.className = 'flex items-center p-4 bg-white bg-opacity-10 rounded-lg mb-4';
            deviceElement.innerHTML = `
                <div class="device-icon">
                    <i class="fas ${iconClass} ${roleColor}"></i>
                </div>
                <div>
                    <h3 class="text-lg font-semibold text-white">${device.name}</h3>
                    <p class="text-sm text-gray-300">IP: ${device.ip} | Role: ${device.role}</p>
                </div>
            `;
            elements.connectedDevicesContainer.appendChild(deviceElement);
        });
    }

    // --- Manual Scan Button (for redundancy/refresh) ---
    elements.scanBtn.addEventListener('click', () => {
        // Instead of fetch, we just ask the server to re-broadcast the current list.
        socket.emit('get_initial_devices');
        console.log('Requested a manual refresh of the device list.');
    });

    // --- CORS Origins Dropdown and Modal Logic ---
    elements.originsBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        elements.originsDropdown.classList.toggle('hidden');
    });

    document.addEventListener('click', () => elements.originsDropdown.classList.add('hidden'));

    const openModal = (modalId) => document.getElementById(modalId).classList.remove('opacity-0', 'pointer-events-none');
    const closeModal = (modalId) => document.getElementById(modalId).classList.add('opacity-0', 'pointer-events-none');

    elements.addOriginBtn.addEventListener('click', (e) => { e.preventDefault(); openModal('addOriginModal'); });
    elements.deleteOriginBtn.addEventListener('click', (e) => { e.preventDefault(); openModal('deleteOriginModal'); });

    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => closeModal(btn.closest('.modal').id));
    });

    elements.submitAddOriginBtn.addEventListener('click', () => handleOriginAction('/admin/add_origin', 'POST', elements.addOriginInput, elements.addOriginMessage));
    elements.submitDeleteOriginBtn.addEventListener('click', () => handleOriginAction('/admin/delete_origin', 'DELETE', elements.deleteOriginInput, elements.deleteOriginMessage));

    async function handleOriginAction(endpoint, method, inputElement, messageElement) {
        const origin = inputElement.value;
        if (!origin) {
            messageElement.textContent = 'Please enter a valid origin URL.';
            messageElement.className = 'mt-4 text-sm text-red-500';
            return;
        }

        try {
            const response = await fetch(endpoint, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ origin }),
            });
            const data = await response.json();
            if (response.ok) {
                messageElement.textContent = data.message || 'Action successful!';
                messageElement.className = 'mt-4 text-sm text-green-500';
                inputElement.value = '';
            } else {
                throw new Error(data.error || 'Failed to perform action.');
            }
        } catch (error) {
            messageElement.textContent = error.message;
            messageElement.className = 'mt-4 text-sm text-red-500';
        }
    }

    // --- 3D Model Rendering (unchanged) ---
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true });
    renderer.setSize(300, 300);
    const modelContainer = document.getElementById('device-model');
    if(modelContainer) modelContainer.appendChild(renderer.domElement);

    const geometry = new THREE.TorusKnotGeometry(1.5, 0.4, 100, 16);
    const material = new THREE.MeshNormalMaterial({ wireframe: false });
    const knot = new THREE.Mesh(geometry, material);
    scene.add(knot);

    camera.position.z = 5;

    function animate() {
        requestAnimationFrame(animate);
        knot.rotation.x += 0.005;
        knot.rotation.y += 0.005;
        renderer.render(scene, camera);
    }
    if(modelContainer) animate();
});