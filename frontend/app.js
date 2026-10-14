const API_URL = window.location.port === '3000'
    ? 'http://localhost:8000'
    : `${window.location.origin}/api`;

const TOKEN_KEY = 'todo_token';

const statusMessage = document.getElementById('statusMessage');
const authSection = document.getElementById('authSection');
const appSection = document.getElementById('appSection');
const logoutBtn = document.getElementById('logoutBtn');
const statusFilter = document.getElementById('statusFilter');

// UI state: which tab is active on the auth card.
let authMode = 'login';

function setStatus(message, isError = false) {
    statusMessage.textContent = message;
    statusMessage.classList.toggle('error', isError);
}

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
}

/**
 * Central fetch wrapper: prefixes the API URL and attaches the JWT as a
 * Bearer token whenever one is stored.
 */
async function request(path, options = {}) {
    const headers = Object.assign({}, options.headers);
    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${path}`, { ...options, headers });

    let payload = null;
    try {
        payload = await response.json();
    } catch {
        payload = null;
    }

    if (!response.ok) {
        // Expired / invalid token: drop it and return to the login screen.
        if (response.status === 401 && getToken()) {
            clearToken();
            showAuthView();
            throw new Error('Your session expired. Please log in again.');
        }
        let detail = payload?.detail || `Request failed (${response.status})`;
        if (Array.isArray(detail)) {
            detail = detail.map(item => item.msg).join(', ');
        }
        throw new Error(detail);
    }

    return payload;
}

// --------------------------------------------------------------------------- //
// Auth
// --------------------------------------------------------------------------- //
function setAuthMode(mode) {
    authMode = mode;
    document.getElementById('tabLogin').classList.toggle('active', mode === 'login');
    document.getElementById('tabSignup').classList.toggle('active', mode === 'signup');
    document.getElementById('authSubmit').textContent = mode === 'login' ? 'Log in' : 'Sign up';
    document.getElementById('password').autocomplete =
        mode === 'login' ? 'current-password' : 'new-password';
}

async function handleAuthSubmit(event) {
    event.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    try {
        let data;
        if (authMode === 'signup') {
            data = await request('/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
        } else {
            // OAuth2 password flow expects form-encoded fields.
            data = await request('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ username, password })
            });
        }

        setToken(data.access_token);
        setStatus(authMode === 'signup' ? 'Account created!' : '');
        showAppView();
        await fetchTasks();
    } catch (error) {
        setStatus(error.message, true);
    }
}

function logout() {
    clearToken();
    document.getElementById('authForm').reset();
    showAuthView();
    setStatus('Logged out.');
}

function showAuthView() {
    authSection.hidden = false;
    appSection.hidden = true;
    logoutBtn.hidden = true;
}

function showAppView() {
    authSection.hidden = true;
    appSection.hidden = false;
    logoutBtn.hidden = false;
}

// --------------------------------------------------------------------------- //
// Tasks
// --------------------------------------------------------------------------- //
async function fetchTasks() {
    const filter = statusFilter ? statusFilter.value : '';
    const query = filter ? `?status=${encodeURIComponent(filter)}` : '';
    try {
        const tasks = await request(`/tasks${query}`);
        displayTasks(tasks);
        setStatus('');
    } catch (error) {
        displayTasks([]);
        setStatus(`Could not load tasks: ${error.message}`, true);
    }
}

async function createTask(payload) {
    try {
        await request('/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        setStatus('Task saved.');
        await fetchTasks();
    } catch (error) {
        setStatus(`Could not save task: ${error.message}`, true);
    }
}

async function updateTask(id, changes) {
    try {
        await request(`/tasks/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(changes)
        });
        await fetchTasks();
    } catch (error) {
        setStatus(`Could not update task: ${error.message}`, true);
    }
}

async function deleteTask(id) {
    try {
        await request(`/tasks/${id}`, { method: 'DELETE' });
        setStatus('Task deleted.');
        await fetchTasks();
    } catch (error) {
        setStatus(`Could not delete task: ${error.message}`, true);
    }
}

const STATUS_LABELS = {
    'pending': 'Pending',
    'in-progress': 'In progress',
    'done': 'Done'
};

function displayTasks(tasks) {
    const taskList = document.getElementById('taskList');
    taskList.innerHTML = '';

    if (!tasks.length) {
        const empty = document.createElement('li');
        empty.className = 'empty-state';
        empty.textContent = 'No tasks yet.';
        taskList.appendChild(empty);
        return;
    }

    tasks.forEach(task => {
        const li = document.createElement('li');
        li.className = `task-item status-${task.status}`;

        const main = document.createElement('div');
        main.className = 'task-main';

        const titleSpan = document.createElement('span');
        titleSpan.className = 'task-title';
        titleSpan.textContent = task.title;

        const badge = document.createElement('span');
        badge.className = `badge badge-${task.status}`;
        badge.textContent = STATUS_LABELS[task.status] || task.status;

        main.append(titleSpan, badge);

        if (task.description) {
            const desc = document.createElement('p');
            desc.className = 'task-description';
            desc.textContent = task.description;
            main.appendChild(desc);
        }

        if (task.due_date) {
            const due = document.createElement('span');
            due.className = 'task-due';
            due.textContent = `Due ${task.due_date}`;
            main.appendChild(due);
        }

        // Inline status control.
        const statusSelect = document.createElement('select');
        statusSelect.className = 'select-input status-select';
        ['pending', 'in-progress', 'done'].forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = STATUS_LABELS[value];
            statusSelect.appendChild(option);
        });
        statusSelect.value = task.status;
        statusSelect.addEventListener('change', () => {
            updateTask(task.id, { status: statusSelect.value });
        });

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.textContent = 'Delete';
        deleteBtn.addEventListener('click', () => deleteTask(task.id));

        const controls = document.createElement('div');
        controls.className = 'task-controls';
        controls.append(statusSelect, deleteBtn);

        li.append(main, controls);
        taskList.appendChild(li);
    });
}

// --------------------------------------------------------------------------- //
// Bootstrap
// --------------------------------------------------------------------------- //
function init() {
    document.getElementById('authForm').addEventListener('submit', handleAuthSubmit);
    document.getElementById('tabLogin').addEventListener('click', () => setAuthMode('login'));
    document.getElementById('tabSignup').addEventListener('click', () => setAuthMode('signup'));
    logoutBtn.addEventListener('click', logout);
    statusFilter.addEventListener('change', fetchTasks);

    document.getElementById('taskForm').addEventListener('submit', event => {
        event.preventDefault();
        const title = document.getElementById('taskTitle').value.trim();
        const description = document.getElementById('taskDescription').value.trim();
        const status = document.getElementById('taskStatus').value;
        const dueDate = document.getElementById('taskDueDate').value;

        if (!title) {
            return;
        }

        createTask({
            title,
            description: description || null,
            status,
            due_date: dueDate || null
        });

        document.getElementById('taskForm').reset();
    });

    // Restore the session on reload if a token is already stored.
    if (getToken()) {
        showAppView();
        fetchTasks();
    } else {
        showAuthView();
    }
}

init();
