const API_URL = window.location.port === '3000'
    ? 'http://localhost:8000'
    : `${window.location.origin}/api`;

const statusMessage = document.getElementById('statusMessage');

function setStatus(message, isError = false) {
    statusMessage.textContent = message;
    statusMessage.classList.toggle('error', isError);
}

async function request(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, options);
    let payload = null;
    try {
        payload = await response.json();
    } catch {
        payload = null;
    }
    if (!response.ok) {
        const detail = payload?.detail || `Request failed (${response.status})`;
        throw new Error(detail);
    }
    return payload;
}

async function fetchTasks() {
    try {
        const tasks = await request('/tasks');
        displayTasks(tasks);
        setStatus('');
    } catch (error) {
        displayTasks([]);
        setStatus(`Could not load tasks: ${error.message}`, true);
    }
}

async function createTask(title) {
    try {
        await request('/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        });
        setStatus('Task saved.');
        await fetchTasks();
    } catch (error) {
        setStatus(`Could not save task: ${error.message}`, true);
    }
}

async function updateTask(id, completed) {
    try {
        await request(`/tasks/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ completed })
        });
        await fetchTasks();
    } catch (error) {
        setStatus(`Could not update task: ${error.message}`, true);
    }
}

async function deleteTask(id) {
    try {
        await request(`/tasks/${id}`, { method: 'DELETE' });
        await fetchTasks();
    } catch (error) {
        setStatus(`Could not delete task: ${error.message}`, true);
    }
}

function displayTasks(tasks) {
    const taskList = document.getElementById('taskList');
    taskList.innerHTML = '';

    tasks.forEach(task => {
        const li = document.createElement('li');
        li.className = `task-item ${task.completed ? 'completed' : ''}`;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'task-checkbox';
        checkbox.checked = task.completed;
        checkbox.addEventListener('change', () => {
            updateTask(task.id, checkbox.checked);
        });

        const titleSpan = document.createElement('span');
        titleSpan.className = 'task-title';
        titleSpan.textContent = task.title;

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn';
        deleteBtn.textContent = 'Delete';
        deleteBtn.addEventListener('click', () => deleteTask(task.id));

        li.append(checkbox, titleSpan, deleteBtn);
        taskList.appendChild(li);
    });
}

function init() {
    document.getElementById('taskForm').addEventListener('submit', event => {
        event.preventDefault();
        const taskTitle = document.getElementById('taskTitle');
        const title = taskTitle.value.trim();
        if (title) {
            createTask(title);
            taskTitle.value = '';
        }
    });

    fetchTasks();
}

init();
