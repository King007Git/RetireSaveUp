// Use relative path since it's served directly by FastAPI
const BASE_URL = "/blackrock/challenge/v1"; 
let historyData = [];

// Default JSON Template
const defaultPayload = {
    "age": 29,
    "wage": 50000,
    "inflation": 5.5,
    "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
    "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-31 19:59:59"}],
    "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
    "transactions": [
        {"date": "2023-02-28 15:49:20", "amount": 375},
        {"date": "2023-07-01 21:59:00", "amount": 620},
        {"date": "2023-10-12 20:15:30", "amount": 250}
    ]
};

// Initialize Textarea
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById('jsonPayload').value = JSON.stringify(defaultPayload, null, 2);
    checkAuthStatus();
});

// --- UI Helpers ---
function switchTab(tab) {
    document.getElementById('alertBox').classList.add('hidden');
    if (tab === 'login') {
        document.getElementById('tab-login').classList.add('active');
        document.getElementById('tab-register').classList.remove('active');
        document.getElementById('loginForm').classList.remove('hidden');
        document.getElementById('registerForm').classList.add('hidden');
    } else {
        document.getElementById('tab-register').classList.add('active');
        document.getElementById('tab-login').classList.remove('active');
        document.getElementById('registerForm').classList.remove('hidden');
        document.getElementById('loginForm').classList.add('hidden');
    }
}

function showAlert(message, type = 'danger') {
    const alertBox = document.getElementById('alertBox');
    alertBox.className = `alert alert-${type} mb-4`;
    alertBox.innerText = message;
    alertBox.classList.remove('hidden');
    setTimeout(() => alertBox.classList.add('hidden'), 5000);
}

// --- Auth State ---
function checkAuthStatus() {
    const token = localStorage.getItem('access_token');
    if (token) {
        document.getElementById('authView').classList.add('hidden');
        document.getElementById('homeView').classList.remove('hidden');
        document.getElementById('logoutBtn').classList.remove('hidden');
        fetchHistory(); 
    } else {
        document.getElementById('authView').classList.remove('hidden');
        document.getElementById('homeView').classList.add('hidden');
        document.getElementById('logoutBtn').classList.add('hidden');
    }
}

function logout() {
    localStorage.removeItem('access_token');
    checkAuthStatus();
}

// --- API Calls ---
async function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem('access_token');
    if (!options.headers) options.headers = {};
    if (token) options.headers['Authorization'] = `Bearer ${token}`;
    
    const response = await fetch(url, options);
    if (response.status === 401) {
        logout();
        showAlert("Session expired. Please log in again.");
        throw new Error("Unauthorized");
    }
    return response;
}

// Registration
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;

    try {
        const response = await fetch(`${BASE_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();
        if (response.ok) {
            showAlert('Registration successful! Please log in.', 'success');
            switchTab('login');
        } else {
            showAlert(data.detail || 'Registration failed');
        }
    } catch (err) { showAlert('Network error.'); }
});

// Login
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    console.log("hii");
    e.preventDefault();

    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const formData = new URLSearchParams();
        formData.append("username", email);  // IMPORTANT: username, not email
        formData.append("password", password);

        const response = await fetch(`${BASE_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem('access_token', data.access_token);
            document.getElementById('alertBox').classList.add('hidden');
            checkAuthStatus();
        } else {
            showAlert(data.detail || 'Invalid credentials');
        }
    } catch (err) {
        showAlert('Network error.');
    }
});

// Submit Calculation
async function submitCalculation(type) {
    let payload;
    try {
        payload = JSON.parse(document.getElementById('jsonPayload').value);
    } catch (e) {
        showAlert('Invalid JSON format in the input box.');
        return;
    }

    try {
        const response = await fetchWithAuth(`${BASE_URL}/returns:${type}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showAlert(`Calculation for ${type.toUpperCase()} successful!`, 'success');
            document.getElementById('calcResultContainer').classList.remove('hidden');
            document.getElementById('calcResultText').innerText = JSON.stringify(data, null, 2);
            fetchHistory();
        } else {
            let err = data.detail;
            if(Array.isArray(err)) err = err.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
            showAlert(`Error: ${err}`);
        }
    } catch (err) {
        if(err.message !== "Unauthorized") showAlert('Failed to calculate.');
    }
}

// Fetch & Render History
async function fetchHistory() {
    const tbody = document.getElementById('historyTableBody');
    tbody.innerHTML = `<tr><td colspan="4" class="text-muted">Loading...</td></tr>`;
    
    try {
        const response = await fetchWithAuth(`${BASE_URL}/history`);
        historyData = await response.json();
        
        if (historyData.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-muted">No calculations found.</td></tr>`;
            return;
        }

        tbody.innerHTML = historyData.map((record, index) => {
            const dateObj = new Date(record.created_at);
            const formattedDate = `${dateObj.toLocaleDateString()} ${dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
            
            const totalAmt = record.result?.totalTransactionAmount || 0;
            const badgeClass = record.investment_type === 'nps' ? 'bg-success' : 'bg-warning text-dark';

            return `
                <tr>
                    <td class="small">${formattedDate}</td>
                    <td><span class="badge ${badgeClass}">${record.investment_type.toUpperCase()}</span></td>
                    <td class="fw-bold">₹${totalAmt}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewDetails(${index})">View</button>
                    </td>
                </tr>
            `;
        }).join('');
        
    } catch (err) {
        if(err.message !== "Unauthorized") {
            tbody.innerHTML = `<tr><td colspan="4" class="text-danger">Failed to load history.</td></tr>`;
        }
    }
}

// View details in Modal
function viewDetails(index) {
    const record = historyData[index];
    if (!record) return;

    document.getElementById('modalPayload').innerText = JSON.stringify(record.payload, null, 2);
    document.getElementById('modalResult').innerText = JSON.stringify(record.result, null, 2);
    
    const modal = new bootstrap.Modal(document.getElementById('detailsModal'));
    modal.show();
}