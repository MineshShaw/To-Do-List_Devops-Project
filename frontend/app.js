const API_URL = window.location.origin + '/api';

async function fetchTasks() {
    try {
        const storedKey = localStorage.getItem('todoApiKey');
        const apiKey = storedKey || '';
        const response = await fetch(`${API_URL}/tasks`, {
            headers: { 'X-API-Key': apiKey }
        });
        const tasks = await response.json();
        displayTasks(tasks);
    } catch (error) {
        console.error('Error fetching tasks:', error);
    }
}

async function createTask(title) {
    try {
        const storedKey = localStorage.getItem('todoApiKey');
        const apiKey = storedKey || '';
        await fetch(`${API_URL}/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            },
            body: JSON.stringify({ title })
        });
        fetchTasks();
    } catch (error) {
        console.error('Error creating task:', error);
    }
}

async function updateTask(id, completed) {
    try {
        const storedKey = localStorage.getItem('todoApiKey');
        const apiKey = storedKey || '';
        await fetch(`${API_URL}/tasks/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            },
            body: JSON.stringify({ completed })
        });
        fetchTasks();
    } catch (error) {
        console.error('Error updating task:', error);
    }
}

async function deleteTask(id) {
    try {
        const storedKey = localStorage.getItem('todoApiKey');
        const apiKey = storedKey || '';
        await fetch(`${API_URL}/tasks/${id}`, {
            method: 'DELETE',
            headers: { 'X-API-Key': apiKey }
        });
        fetchTasks();
    } catch (error) {
        console.error('Error deleting task:', error);
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
        deleteBtn.addEventListener('click', () => {
            deleteTask(task.id);
        });
        
        li.appendChild(checkbox);
        li.appendChild(titleSpan);
        li.appendChild(deleteBtn);
        taskList.appendChild(li);
    });
}

function init() {
    const taskForm = document.getElementById('taskForm');
    const taskTitle = document.getElementById('taskTitle');
    
    taskForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const title = taskTitle.value.trim();
        if (title) {
            createTask(title);
            taskTitle.value = '';
        }
    });
    
    fetchTasks();
}

init();
