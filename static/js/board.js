let globalTasks = []; 
let currentModalTaskId = null;

// Pełne polskie tłumaczenia kolumn na tablicy Kanban
const columns = {
    'inbox': { title: 'Nowe', color: 'bg-gray-200 text-gray-700' },
    'do_first': { title: 'Zrób najpierw', color: 'bg-red-100 text-red-700' },
    'schedule': { title: 'Zaplanuj', color: 'bg-blue-100 text-blue-700' },
    'delegate': { title: 'Oddeleguj', color: 'bg-yellow-100 text-yellow-700' },
    'do_now': { title: 'W trakcie', color: 'bg-orange-100 text-orange-700' },
    'done': { title: 'Zakończone', color: 'bg-green-200 text-green-800' } 
};

window.onload = () => {
    initBoard();
    loadTasks();
};

function initBoard() {
    const board = document.getElementById('board');
    board.innerHTML = '';
    for (const [key, val] of Object.entries(columns)) {
        board.innerHTML += `
            <div class="bg-[#EBECF0] rounded-xl flex flex-col w-80 flex-shrink-0 border border-gray-200 max-h-full">
                <div class="p-3 font-bold text-gray-700 flex justify-between items-center rounded-t-xl bg-gradient-to-b from-white/50 to-transparent">
                    <span class="text-xs uppercase tracking-wider font-extrabold">${val.title}</span>
                    <span id="count-${key}" class="text-[10px] ${val.color} px-2 py-0.5 rounded-full font-black shadow-sm">0</span>
                </div>
                <div id="col-${key}" class="p-3 flex-1 overflow-y-auto space-y-3 column-drop-zone" ondrop="drop(event, '${key}')" ondragover="allowDrop(event)"></div>
            </div>`;
    }
}

// ZASTOSOWANIE NOWEJ FUNKCJI fetchWithAuth
async function loadTasks() {
    try {
        const res = await fetchWithAuth(`${CONFIG.API_URL}/tasks/`);
        // fetchWithAuth automatycznie obsłuży błąd 401 i wylogowanie!
        if (!res.ok) throw new Error("Błąd pobierania danych");
        globalTasks = await res.json();
        renderTasks(globalTasks);
    } catch (e) { console.error(e); }
}

function renderTasks(tasks) {
    Object.keys(columns).forEach(k => document.getElementById(`col-${k}`).innerHTML = '');
    
    tasks.forEach(task => {
        const colKey = columns[task.priority_ai] ? task.priority_ai : 'inbox';
        const col = document.getElementById(`col-${colKey}`);
        
        const card = document.createElement('div');
        card.id = `task-${task.id}`;
        card.draggable = true;
        card.ondragstart = (e) => drag(e, task.id);
        card.onclick = () => openModal(task.id); 
        card.className = "task-card bg-white p-4 rounded-xl shadow-sm cursor-pointer border border-gray-200 relative group";
        
        let timeColor = task.logged_time_minutes > task.estimated_time_minutes ? 'bg-red-50 text-red-600 border-red-100' : 'bg-gray-50 text-gray-600 border-gray-100';
        
        card.innerHTML = `
            <div class="text-sm font-semibold text-gray-800 mb-3 pr-6 leading-tight">${task.title}</div>
            <div class="flex justify-between items-center mt-3 pt-3 border-t border-gray-100">
                <span class="text-[10px] border px-2 py-1 rounded-md font-bold flex items-center gap-1 ${timeColor}">
                    Czas: ${task.logged_time_minutes} / ${task.estimated_time_minutes}m
                </span>
                <div class="flex gap-2">
                    <button onclick="event.stopPropagation(); decomposeTask(${task.id})" class="text-indigo-600 hover:text-white transition bg-indigo-50 hover:bg-indigo-500 text-[10px] px-2 py-1 rounded font-bold uppercase tracking-wide" title="Rozbij zadanie przez AI">Rozbij</button>
                    <button onclick="event.stopPropagation(); deleteTask(${task.id})" class="text-red-500 hover:text-white hover:bg-red-500 text-[10px] px-2 py-1 rounded font-bold uppercase tracking-wide opacity-0 group-hover:opacity-100 transition" title="Usuń">Usuń</button>
                </div>
            </div>
        `;
        col.appendChild(card);
    });
    Object.keys(columns).forEach(k => document.getElementById(`count-${k}`).innerText = document.getElementById(`col-${k}`).children.length);
}

function openModal(taskId) {
    currentModalTaskId = taskId;
    const task = globalTasks.find(t => t.id === taskId);
    if(!task) return;

    document.getElementById('modalTitle').innerText = task.title;
    document.getElementById('modalDesc').innerText = task.description || 'Brak opisu.';
    document.getElementById('modalStatusBadge').innerText = columns[task.priority_ai || 'inbox'].title;
    document.getElementById('modalEstTime').innerText = task.estimated_time_minutes;
    document.getElementById('modalLoggedTimeInput').value = task.logged_time_minutes;

    renderComments(task.comments || []);
    document.getElementById('taskModal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('taskModal').classList.add('hidden');
    currentModalTaskId = null;
}

function renderComments(comments) {
    const list = document.getElementById('modalCommentsList');
    if (comments.length === 0) {
        list.innerHTML = '<p class="text-xs text-gray-400 italic">Brak notatek. Dodaj pierwszą poniżej.</p>';
        return;
    }
    list.innerHTML = comments.map(c => `
        <div class="bg-indigo-50/50 p-3 rounded-xl border border-indigo-50">
            <p class="text-sm text-gray-700">${c.text}</p>
            <span class="text-[9px] font-bold text-gray-400 mt-2 uppercase tracking-wider block">${new Date(c.created_at).toLocaleString()}</span>
        </div>
    `).join('');
}

async function saveTime() {
    const task = globalTasks.find(t => t.id === currentModalTaskId);
    const newTime = parseInt(document.getElementById('modalLoggedTimeInput').value) || 0;
    
    const payload = {
        title: task.title, description: task.description, status: task.status,
        priority_ai: task.priority_ai, estimated_time_minutes: task.estimated_time_minutes,
        logged_time_minutes: newTime
    };

    try {
        await fetchWithAuth(`${CONFIG.API_URL}/tasks/${task.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        await loadTasks(); 
        openModal(task.id); 
    } catch (e) { alert("Błąd zapisu"); }
}

async function addComment() {
    const input = document.getElementById('newCommentText');
    const text = input.value.trim();
    if (!text) return;

    try {
        await fetchWithAuth(`${CONFIG.API_URL}/tasks/${currentModalTaskId}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        input.value = '';
        await loadTasks();
        openModal(currentModalTaskId);
    } catch (e) { alert("Błąd dodawania notatki"); }
}

function allowDrop(ev) { ev.preventDefault(); }
function drag(ev, taskId) { 
    ev.dataTransfer.setData("taskId", taskId); 
    setTimeout(() => document.getElementById(`task-${taskId}`).classList.add('dragging'), 0); 
}
document.addEventListener('dragend', (e) => { 
    if (e.target.classList.contains('dragging')) e.target.classList.remove('dragging'); 
});

async function drop(ev, newColumnKey) {
    ev.preventDefault();
    const taskId = ev.dataTransfer.getData("taskId");
    const task = globalTasks.find(t => t.id == taskId);
    if (!task || task.priority_ai === newColumnKey) return;

    document.getElementById(`col-${newColumnKey}`).appendChild(document.getElementById(`task-${taskId}`));
    
    const payload = {
        title: task.title, description: task.description, status: task.status,
        priority_ai: newColumnKey, // POPRAWKA: zawsze wysyłamy klucz kolumny
        estimated_time_minutes: task.estimated_time_minutes, logged_time_minutes: task.logged_time_minutes
    };

    try {
        await fetchWithAuth(`${CONFIG.API_URL}/tasks/${taskId}`, {
            method: 'PUT', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        await loadTasks();
    } catch (e) { loadTasks(); }
}

async function createManualTask() {
    const title = document.getElementById('manualTitle').value.trim();
    const desc = document.getElementById('manualDesc').value.trim();
    const time = parseInt(document.getElementById('manualTime').value);

    if (!title) return alert("Podaj tytuł zadania!");

    try {
        const res = await fetchWithAuth(`${CONFIG.API_URL}/tasks/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                description: desc,
                estimated_time_minutes: time || 60,
                priority_ai: "inbox",
                status: "inbox"
            })
        });

        if (res.ok) {
            document.getElementById('manualTaskModal').classList.add('hidden');
            document.getElementById('manualTitle').value = '';
            document.getElementById('manualDesc').value = '';
            await loadTasks(); 
        }
    } catch (e) {
        alert("Błąd podczas tworzenia zadania.");
    }
}

async function sendToAI() {
    const text = document.getElementById('aiInput').value.trim();
    if (!text) return;
    document.getElementById('aiBtnText').classList.add('hidden');
    document.getElementById('aiLoader').classList.remove('hidden');
    try {
        await fetchWithAuth(`${CONFIG.API_URL}/tasks/smart-inbox`, {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        document.getElementById('aiInput').value = '';
        await loadTasks();
    } catch (e) { alert("Błąd AI"); } finally {
        document.getElementById('aiBtnText').classList.remove('hidden');
        document.getElementById('aiLoader').classList.add('hidden');
    }
}

async function decomposeTask(taskId) { 
    await fetchWithAuth(`${CONFIG.API_URL}/tasks/${taskId}/decompose`, { method: 'POST' }); 
    await loadTasks(); 
}

async function deleteTask(taskId) { 
    if(confirm("Czy na pewno chcesz bezpowrotnie usunąć to zadanie?")) { 
        await fetchWithAuth(`${CONFIG.API_URL}/tasks/${taskId}`, { method: 'DELETE' }); 
        await loadTasks(); 
    } 
}

async function clearAllTasks() {
    if(globalTasks.length === 0) {
        alert("Tablica jest już pusta.");
        return;
    }
    
    if(confirm("CZY NA PEWNO chcesz usunąć WSZYSTKIE zadania? Tej akcji nie można cofnąć!")) {
        try {
            const deletePromises = globalTasks.map(task => 
                fetchWithAuth(`${CONFIG.API_URL}/tasks/${task.id}`, { method: 'DELETE' })
            );
            
            await Promise.all(deletePromises);
            await loadTasks(); 
            alert("Wszystkie zadania zostały usunięte.");
        } catch (e) {
            alert("Wystąpił błąd podczas usuwania zadań.");
        }
    }
}