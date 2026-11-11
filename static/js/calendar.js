let calendar;
let allTasksRaw = []; // Будем хранить полный массив задач, чтобы быстро доставать описание

const eventColors = {
    'do_first': '#ef4444', 'schedule': '#3b82f6', 'delegate': '#eab308',
    'do_now': '#f97316', 'done': '#22c55e', 'inbox': '#94a3b8'
};

document.addEventListener('DOMContentLoaded', function() {
    initCalendar();
});

async function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    const events = await fetchCalendarEvents();

    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        locale: 'pl',
        firstDay: 1,
        slotMinTime: '08:00:00',
        slotMaxTime: '20:00:00',
        allDaySlot: false,
        nowIndicator: true,
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridWeek,timeGridDay'
        },
        events: events,
        eventClick: function(info) {
            openTaskModal(info.event.id); 
        }
    });

    calendar.render();
}

async function fetchCalendarEvents() {
    try {
        // ИСПОЛЬЗУЕМ НОВУЮ ФУНКЦИЮ fetchWithAuth (она сама обработает 401 ошибку)
        const res = await fetchWithAuth(`${CONFIG.API_URL}/tasks/`);
        if (!res.ok) throw new Error("Błąd pobierania zadań");
        
        allTasksRaw = await res.json(); 
        const events = [];

        allTasksRaw.forEach(task => {
            if (task.status !== 'done' && task.scheduled_start && task.scheduled_end) {
                events.push({
                    id: task.id.toString(),
                    title: task.title,
                    start: task.scheduled_start,
                    end: task.scheduled_end,
                    backgroundColor: eventColors[task.priority_ai] || eventColors['inbox']
                });
            }
        });
        return events;
    } catch (e) {
        console.error("Błąd pobierania zadań:", e);
        return [];
    }
}

// ФУНКЦИЯ ВЫЗОВА ИИ ОПТИМИЗАЦИИ
async function rescheduleAI() {
    const btn = document.getElementById('rescheduleBtn');
    const daysRange = parseInt(document.getElementById('daysRange').value);
    const productivityMode = document.getElementById('prodMode').value;
    
    const originalText = btn.innerHTML;
    btn.innerHTML = `🌀 Reorganizacja...`;
    btn.disabled = true;

    startDinoGame();

    try {
        // fetchWithAuth автоматически превратит объект body в JSON строку и добавит заголовки
        const res = await fetchWithAuth(`${CONFIG.API_URL}/tasks/reschedule-ai`, {
            method: 'POST',
            body: { days_range: daysRange, productivity_mode: productivityMode }
        });

        if (!res.ok) throw new Error("Błąd API");

        const data = await res.json();
        console.log("%c🧠 LOGI MYŚLOWE AI (Chain of Thought):", "color: #a855f7; font-weight: bold; font-size: 14px;");
        console.log(`%c${data.ai_thoughts}`, "color: #4b5563; font-style: italic;");

        const freshEvents = await fetchCalendarEvents();
        calendar.removeAllEvents();
        calendar.addEventSource(freshEvents);
        
        setTimeout(() => {
            alert("Sukces! Harmonogram zaktualizowany przez AI zgodnie z Twoim profilem.");
        }, 100);
        
    } catch (e) {
        alert("Wystąpił błąd podczas planowania AI.");
    } finally {
        stopDinoGame();
        
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ФУНКЦИЯ ПОЛНОЙ ОЧИСТКИ КАЛЕНДАРЯ
async function clearCalendar() {
    if (!confirm("Czy na pewno chcesz usunąć wszystkie zaplanowane terminy z kalendarza?")) return;

    try {
        // Упрощенный вызов через fetchWithAuth
        const res = await fetchWithAuth(`${CONFIG.API_URL}/tasks/reset-schedule`, {
            method: 'POST'
        });

        if (res.ok) {
            calendar.removeAllEvents();
            alert("Siatka czasu została wyczyszczona!");
        }
    } catch (e) {
        alert("Błąd resetowania siatki.");
    }
}

// ЛОГИКА РАБОТЫ МОДАЛЬНОГО ОКНА
function openTaskModal(taskId) {
    const task = allTasksRaw.find(t => t.id.toString() === taskId);
    if (!task) return;

    document.getElementById('modalTitle').innerText = task.title;
    document.getElementById('modalDesc').innerText = task.description || "Brak opisu.";
    document.getElementById('modalTime').innerText = task.estimated_time_minutes || "60";
    
    const badge = document.getElementById('modalPriority');
    badge.innerText = task.priority_ai || 'inbox';
    
    if (task.priority_ai === 'do_first') {
        badge.className = "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-red-100 text-red-800";
    } else {
        badge.className = "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-100 text-blue-800";
    }

    document.getElementById('taskModal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('taskModal').classList.add('hidden');
}

function startDinoGame() {
    const modal = document.getElementById('dinoModal');
    const iframe = document.getElementById('dinoFrame');
    
    iframe.src = "/dino.html"; 
    modal.classList.remove('hidden');

    iframe.onload = function() {
        iframe.contentWindow.focus();
    };
}

function stopDinoGame() {
    const modal = document.getElementById('dinoModal');
    const iframe = document.getElementById('dinoFrame');
    
    modal.classList.add('hidden');
    iframe.src = ""; 
}