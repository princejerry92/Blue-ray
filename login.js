document.addEventListener('DOMContentLoaded', () => {

    const loginForm = document.getElementById('login-form');
    const feedbackModal = document.getElementById('feedbackModal');
    const errorModal = document.getElementById('errorModal');
    const closeFeedbackModal = document.getElementById('closeFeedbackModal');
    const closeErrorModal = document.getElementById('closeErrorModal');
    const errorMessageElement = document.getElementById('errorMessage');

    // --- Main Login Form Submission ---
    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const username = document.getElementById('username').value.trim().toLowerCase();
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/check_password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) { // Check for 2xx status codes
                feedbackModal.classList.remove('hidden');
                // After 200ms delay, show admin selection modal instead of redirecting immediately
                setTimeout(() => {
                    feedbackModal.classList.add('hidden');
                    adminSelectModal.classList.remove('hidden');
                }, 200);
            } else {
                // Use the error message from the server
                errorMessageElement.textContent = data.error || 'Login failed. Please check your credentials.';
                errorModal.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Login Error:', error);
            errorMessageElement.textContent = 'A network error occurred. Please try again.';
            errorModal.classList.remove('hidden');
        }
    });
    
    closeFeedbackModal.addEventListener('click', () => {
        window.location.href = '/home';
    });

    // Admin selection modal HTML
    const adminSelectModalHTML = `
        <div id="adminSelectModal" class="modal hidden">
            <div class="modal-content">
                <h2 class="text-xl font-bold mb-4">Select Admin Type</h2>
                <p>Please select your admin type to continue:</p>
                <div class="admin-buttons mt-4">
                    <button id="admin1Btn" class="modal-button mr-4">Admin 1</button>
                    <button id="admin2Btn" class="modal-button">Admin 2</button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', adminSelectModalHTML);

    const adminSelectModal = document.getElementById('adminSelectModal');
    const admin1Btn = document.getElementById('admin1Btn');
    const admin2Btn = document.getElementById('admin2Btn');

    // Admin selection button handlers
    admin1Btn.addEventListener('click', () => {
        window.location.href = '/Admin1'; // Redirect to Admin 1 home page
    });

    admin2Btn.addEventListener('click', () => {
        window.location.href = '/Admin2'; // Redirect to Admin 2 home page
    });

    closeErrorModal.addEventListener('click', () => {
        errorModal.classList.add('hidden');
    });

    // --- "Add New Admin" Modal Logic ---
    document.getElementById('add-admin-link').addEventListener('click', () => {
        const modalHTML = `
            <div id="add-admin-modal" class="modal">
                <div class="modal-content">
                    <span class="modal-close" onclick="this.parentElement.parentElement.remove()">×</span>
                    <h2 class="text-xl font-bold mb-4">Add New Admin</h2>
                    <form id="add-admin-form">
                        <div class="form-group">
                            <label for="new_username">Username:</label>
                            <input type="text" id="new_username" name="username" required>
                        </div>
                        <div class="form-group">
                            <label for="new_password">New Password (must start with '@'):</label>
                            <div class="relative">
                                <input type="password" id="new_password" required>
                                <span class="view-password" onclick="togglePasswordVisibility('new_password')"><i class="fas fa-eye-slash"></i></span>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="confirm_password">Confirm Password:</label>
                            <div class="relative">
                                <input type="password" id="confirm_password" required>
                                <span class="view-password" onclick="togglePasswordVisibility('confirm_password')"><i class="fas fa-eye-slash"></i></span>
                            </div>
                            <span id="password-mismatch" class="text-red-500 text-sm mt-1" style="display: none;">Passwords do not match.</span>
                        </div>
                        <button type="submit" class="w-full modal-button">Add Admin</button>
                    </form>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Add event listener to the newly created form
        const addAdminForm = document.getElementById('add-admin-form');
        addAdminForm.addEventListener('submit', handleAddAdminSubmit);
    });

    async function handleAddAdminSubmit(event) {
        event.preventDefault();
        const username = document.getElementById('new_username').value.trim().toLowerCase();
        const newPassword = document.getElementById('new_password').value;
        const confirmPassword = document.getElementById('confirm_password').value;
        const mismatchError = document.getElementById('password-mismatch');

        mismatchError.style.display = 'none';

        if (newPassword !== confirmPassword) {
            mismatchError.style.display = 'block';
            return;
        }

        if (!newPassword.startsWith('@')) {
            alert("Password must start with '@'.");
            return;
        }

        try {
            const response = await fetch('/new_admin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username, password: newPassword })
            });
            const result = await response.json();
            
            if (response.ok) {
                alert(result.message || "Admin created successfully!");
                document.getElementById('add-admin-modal').remove();
            } else {
                alert(result.error || "Failed to create admin.");
            }
        } catch (error) {
            console.error('Add Admin Error:', error);
            alert('An error occurred while creating the new admin.');
        }
    }
    
    // --- Generic Modal for Nav Links ---
    const genericModal = document.getElementById('genericModal');
    const genericModalBody = document.getElementById('genericModalBody');
    const genericModalClose = genericModal.querySelector('.modal-close');

    function openGenericModal(content) {
        genericModalBody.innerHTML = content;
        genericModal.classList.remove('hidden');
    }
    genericModalClose.addEventListener('click', () => genericModal.classList.add('hidden'));
    genericModal.addEventListener('click', (e) => {
        if (e.target === genericModal) genericModal.classList.add('hidden');
    });

    document.getElementById('gamesLink').addEventListener('click', () => {
        openGenericModal(`
            <i class="fas fa-gamepad modal-icon"></i>
            <h2 class="text-xl font-bold mb-4">Welcome to Our Game Site</h2>
            <a href="https://articfoxinc.my.canva.site/" target="_blank" class="modal-button">Play Now</a>
        `);
    });
    document.getElementById('learningLink').addEventListener('click', () => {
        openGenericModal(`
            <i class="fas fa-book modal-icon"></i>
            <h2 class="text-xl font-bold mb-4">Choose Your Learning Resource</h2>
            <a href="https://articfoxinc.my.canva.site/" target="_blank" class="modal-button">Go to Resources</a>
        `);
    });
    document.getElementById('updatesLink').addEventListener('click', () => {
        openGenericModal(`
            <i class="fas fa-sync-alt modal-icon"></i>
            <h2 class="text-xl font-bold mb-4">Check New Updates</h2>
            <div class="social-links text-3xl">
                <a href="https://github.com/princejerry92" target="_blank"><i class="fab fa-github"></i></a>
                <a href="https://twitter.com/@artic_fox92" target="_blank"><i class="fab fa-twitter"></i></a>
                <a href="https://linkedin.com/in/articfox92" target="_blank"><i class="fab fa-linkedin"></i></a>
                <a href="https://wa.me/+2347011853528" target="_blank"><i class="fab fa-whatsapp"></i></a>
            </div>
        `);
    });
    document.getElementById('guideLink').addEventListener('click', () => {
        openGenericModal(`
            <i class="fas fa-question-circle modal-icon"></i>
            <h2 class="text-xl font-bold mb-4">User Guide</h2>
            <p class="mb-4">Would you like to read the guide or watch a demo?</p>
            <a href="https://articfoxinc.my.canva.site/" target="_blank" class="modal-button">Read Guide</a>
            <a href="/video" class="modal-button">Watch Demo</a>
        `);
    });

});

// Helper function to toggle password visibility
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const icon = input.nextElementSibling.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    }
}