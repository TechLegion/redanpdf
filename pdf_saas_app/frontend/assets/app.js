// PDF SaaS App Main JS
const API_BASE = 'http://localhost:8000'; // Change if deploying elsewhere

// Utility: Show alert
function showAlert(message, type = 'danger') {
    let alert = document.getElementById('main-alert');
    if (!alert) {
        alert = document.createElement('div');
        alert.id = 'main-alert';
        alert.style.position = 'fixed';
        alert.style.top = '1.5rem';
        alert.style.right = '1.5rem';
        alert.style.zIndex = 9999;
        document.body.appendChild(alert);
    }
    alert.innerHTML = `<div class="alert alert-${type} shadow">${message}</div>`;
    setTimeout(() => { alert.innerHTML = ''; }, 3500);
}

// Utility: Get auth token
function getToken() {
    return localStorage.getItem('token');
}

// Utility: Set auth token
function setToken(token) {
    localStorage.setItem('token', token);
}

// Utility: Remove auth token
function removeToken() {
    localStorage.removeItem('token');
}

// Sidebar nav active state
function setActiveNav(id) {
    document.querySelectorAll('.sidebar .nav-link').forEach(link => link.classList.remove('active'));
    if (id) document.getElementById(id) ? .classList.add('active');
}

// Add more functions for login, register, upload, list, download, delete, merge, compress, OCR, image-to-PDF as needed.
// Each page (login.html, register.html, index.html) will use these functions.