const modal = document.getElementById('modal');
const modalContent = document.querySelector('.modal-body');
const closeModalButton = document.querySelector('.modal-close');

function viewPassword(id) {
    const passwordInput = document.getElementById(id);
    const viewPasswordIcon = passwordInput.parentElement.querySelector('.view-password i');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        viewPasswordIcon.classList.remove('fa-eye-slash');
        viewPasswordIcon.classList.add('fa-eye');
    } else {
        passwordInput.type = 'password';
        viewPasswordIcon.classList.remove('fa-eye');
        viewPasswordIcon.classList.add('fa-eye-slash');
    }
    }
    
    

// Open modal and set content
function openModal(content) {
    modalContent.innerHTML = content;
    modal.classList.remove('hidden');
}

// Close modal when clicking on the close button
closeModalButton.addEventListener('click', () => {
    modal.classList.add('hidden');
});

// Close modal when clicking outside of it
document.addEventListener('click', (e) => {
    if (e.target === modal) {
        modal.classList.add('hidden');
    }
});

// Games Modal
document.getElementById('gamesLink').addEventListener('click', () => {
    const content = `
        <i class="fas fa-gamepad modal-icon"></i>
        <h2 class="text-xl font-bold mb-4">Welcome to Our Game Site</h2>
        <a href="https://www.mygamesite.com" target="_blank" class="modal-button">Play Now</a>
    `;
    openModal(content);
});

// Learning Modal
document.getElementById('learningLink').addEventListener('click', () => {
    const content = `
        <i class="fas fa-book modal-icon"></i>
        <h2 class="text-xl font-bold mb-4">Choose Your Learning Resource</h2>
        <a href="https://www.learningresource.com" target="_blank" class="modal-button">Go to Resources</a>
    `;
    openModal(content);
});

// Updates Modal
document.getElementById('updatesLink').addEventListener('click', () => {
    const content = `
        <i class="fas fa-sync-alt modal-icon"></i>
        <h2 class="text-xl font-bold mb-4">Check New Updates</h2>
        <div class="social-links">
            <a href="https://github.com" target="_blank"><i class="fab fa-github"></i></a>
            <a href="https://twitter.com" target="_blank"><i class="fab fa-twitter"></i></a>
            <a href="https://linkedin.com" target="_blank"><i class="fab fa-linkedin"></i></a>
            <a href="https://wa.me/1234567890" target="_blank"><i class="fab fa-whatsapp"></i></a>
        </div>
    `;
    openModal(content);
});

// Guide Modal
document.getElementById('guideLink').addEventListener('click', () => {
    const content = `
        <i class="fas fa-question-circle modal-icon"></i>
        <h2 class="text-xl font-bold mb-4">User Guide</h2>
        <p class="mb-4">Would you like to read the guide or watch a demo?</p>
        <a href="https://www.myguide.com" target="_blank" class="modal-button">Read Guide</a>
        <a href="video.html" class="modal-button">Watch Demo</a>
    `;
    openModal(content);
});


document.querySelector('.flex.items-center.mt-4.text-orange-500').addEventListener('click', () => {
    // Create and display the modal
    const modal = document.createElement('div');
    modal.classList.add('modal');
    modal.innerHTML = `
        <div class="modal-content">
            <span class="modal-close">&times;</span>
            <div class="modal-body">
                <h2>Add New Admin</h2>
                <form id="add-admin-form">
                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <div class="relative">
                            <input type="password" id="password" name="password" required>
                            <span class="view-password absolute right-3 top-3 cursor-pointer" onclick="viewPassword('password')">
                                <i class="fas fa-eye-slash"></i>
                            </span>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="confirm-password">Confirm Password:</label>
                        <div class="relative">
                            <input type="password" id="confirm-password" name="confirm-password" required>
                            <span class="view-password absolute right-3 top-3 cursor-pointer" onclick="viewPassword('confirm-password')">
                                <i class="fas fa-eye-slash"></i>
                            </span>
                        </div>
                        <span id="password-mismatch" style="color: red; display: none;">Passwords do not match</span>

                    </div>
                    <div class="form-group">
                        <label for="default-password">Default Password:</label>
                        <div class="relative">
                            <input type="password" id="default-password" name="default-password" required>
                            <span class="view-password absolute right-3 top-3 cursor-pointer" onclick="viewPassword('default-password')">
                                <i class="fas fa-eye-slash"></i>
                            </span>
                        </div>
                    </div>
                    <button type="submit">Add Admin</button>
                </form>
            </div>
        </div>
    `;

// Add the modal to the DOM
document.body.appendChild(modal);

// Handle modal close functionality
document.querySelector('.modal-close').addEventListener('click', () => {
    modal.remove();
});

// Close modal when clicking outside of it
document.addEventListener('click', (e) => {
    if (e.target === modal) {
        modal.classList.add('hidden');
    }
});


// Form submission logic
const form = document.getElementById('add-admin-form');
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value.trim().toLowerCase();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    const defaultPassword = document.getElementById('default-password').value;

    // Check if passwords match
    if (password !== confirmPassword) {
        document.getElementById('password-mismatch').style.display = 'block';
        return;
    } else {
        document.getElementById('password-mismatch').style.display = 'none';
    }

    // Check if password starts with '@'
    if (!password.startsWith('@')) {
        alert('Password must start with @');
        return;
    }

    // Validate default password based on the username
    if (username === 'admin1' && defaultPassword !== '@RoyalRangers') {
        alert('Incorrect default password for admin1');
        return;
    }
    if (username === 'admin2' && defaultPassword !== '@1234ABCD') {
        alert('Incorrect default password for admin2');
        return;
    }

    // Send data to server to add the new admin
    try {
        const response = await fetch('/new_admin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const result = await response.json();

        if (response.ok) {
            alert(result.message);
            modal.remove();
        } else {
            alert(result.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error creating new admin');
    }
});

});