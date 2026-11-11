function checkAuth() {
    const token = localStorage.getItem('token');
    const isAuthPage = window.location.pathname.endsWith('auth.html');

    if (!token && !isAuthPage) {
        window.location.href = '/auth.html';
    }
    if (token && isAuthPage) {
        window.location.href = '/index.html';
    }
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = '/auth.html';
}

// Pomocnicza funkcja do wykonywania bezpiecznych zapytań z tokenem JWT
async function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem('token');
    
    // Inicjalizacja nagłówków, jeśli nie istnieją
    options.headers = options.headers || {};
    
    // Automatyczne dołączanie tokenu autoryzacji
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Jeśli wysyłamy obiekt, automatycznie ustawiamy Content-Type na JSON
    if (options.body && typeof options.body === 'object' && !(options.body instanceof URLSearchParams)) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
    }

    const response = await fetch(url, options);
    
    // Obsługa wygasłego tokenu (błąd 401) - automatyczne wylogowanie
    if (response.status === 401) {
        logout();
    }
    
    return response;
}

// Uruchomienie weryfikacji przy załadowaniu strony
checkAuth();