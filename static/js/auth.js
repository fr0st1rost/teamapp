async function handleLogin(e) {
    e.preventDefault();
    
    const formData = new URLSearchParams();
    formData.append('username', document.getElementById('username').value);
    formData.append('password', document.getElementById('password').value);
    
    try {
        // Dodajemy jawny nagłówek Content-Type wymagany przez OAuth2PasswordRequestForm
        const res = await fetch(`${CONFIG.API_URL}/auth/login`, { 
            method: 'POST', 
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData 
        });
        
        // Wyciągamy szczegóły błędu z FastAPI w przypadku niepowodzenia
        if (!res.ok) {
            const errorDetail = await res.json();
            console.error("Błąd walidacji FastAPI:", errorDetail);
            throw new Error();
        }
        
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        document.getElementById('loginError').classList.add('hidden');
        window.location.href = '/index.html'; // Przekierowanie na stronę główną systemu
    } catch (err) { 
        document.getElementById('loginError').classList.remove('hidden'); 
    }
}