import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

# --- FIXTURY DO AUTORYZACJI ---

@pytest.fixture(scope="module")
def test_user():
    """Tworzy użytkownika testowego i zwraca jego dane"""
    user_data = {
        "email": "tester@example.com",
        "password": "securepassword123",
        "role_id": 1  # Zakładamy, że rola podstawowa ma ID 1
    }
    # Rejestrujemy użytkownika (ignorujemy błąd, jeśli już istnieje)
    client.post("/auth/register", json=user_data)
    return user_data

@pytest.fixture(scope="module")
def auth_headers(test_user):
    """Autoryzuje użytkownika i zwraca nagłówki z tokenem JWT"""
    response = client.post(
        "/auth/login",
        data={"username": test_user["email"], "password": test_user["password"]}
    )
    token = response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_task(auth_headers):
    """Tworzy zadanie testowe przed testem i zwraca jego ID"""
    response = client.post(
        "/tasks/", 
        json={"title": "Testowe Zadanie", "estimated_time_minutes": 60, "priority_ai": "inbox", "status": "inbox"},
        headers=auth_headers
    )
    return response.json()


# --- TESTY AUTORYZACJI (AUTH) ---

def test_register_new_user():
    # Generujemy unikalny email do testu
    payload = {"email": "new_user_999@example.com", "password": "123", "role_id": 1}
    response = client.post("/auth/register", json=payload)
    assert response.status_code in [200, 400] # 200 sukces, 400 jeśli już stworzony wcześniej

def test_login_success(test_user):
    response = client.post("/auth/login", data={"username": test_user["email"], "password": test_user["password"]})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_fail():
    response = client.post("/auth/login", data={"username": "wrong@email.com", "password": "wrongpassword"})
    assert response.status_code == 400


# --- TESTY CRUD ZADAŃ (TASKS) ---

def test_create_task(auth_headers):
    payload = {"title": "Skonfigurować zaporę", "description": "UFW na Ubuntu", "estimated_time_minutes": 45}
    response = client.post("/tasks/", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Skonfigurować zaporę"

def test_get_tasks(auth_headers, test_task):
    response = client.get("/tasks/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

def test_update_task(auth_headers, test_task):
    task_id = test_task["id"]
    payload = {"title": "Zaktualizowany Tytuł", "status": "done"}
    response = client.put(f"/tasks/{task_id}", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Zaktualizowany Tytuł"
    assert response.json()["status"] == "done"

def test_add_comment(auth_headers, test_task):
    task_id = test_task["id"]
    response = client.post(f"/tasks/{task_id}/comments", json={"text": "Testowa notatka"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["text"] == "Testowa notatka"


# --- TESTY ENDPOINTÓW AI (Z WYKORZYSTANIEM MOCK) ---

@patch("app.routers.tasks.process_smart_inbox")
def test_smart_inbox(mock_process, auth_headers):
    # Wskazujemy, co powinna zwrócić "podrobiona" sieć neuronowa
    mock_process.return_value = [{"title": "Zadanie z AI", "priority_ai": "do_first", "estimated_time_minutes": 30}]
    
    response = client.post("/tasks/smart-inbox", json={"text": "Zrób to szybko"}, headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Zadanie z AI"

@patch("app.routers.tasks.decompose_existing_task")
def test_decompose_task(mock_decompose, auth_headers, test_task):
    mock_decompose.return_value = [{"title": "Krok 1", "estimated_time_minutes": 15}]
    
    task_id = test_task["id"]
    response = client.post(f"/tasks/{task_id}/decompose", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Krok 1"

@patch("ollama.Client.chat")
def test_reschedule_ai(mock_ollama_chat, auth_headers, test_task):
    # Modelujemy idealną odpowiedź z Ollama ze strukturą JSON
    mock_ollama_chat.return_value = {
        'message': {'content': f'<mysli>Myślę...</mysli> [{test_task["id"]}]'}
    }
    
    payload = {"days_range": 3, "productivity_mode": "morning"}
    response = client.post("/tasks/reschedule-ai", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@patch("ollama.Client.chat")
def test_generate_report(mock_ollama_chat, auth_headers, test_task):
    # Modelujemy odpowiedź dla raportu
    mock_ollama_chat.return_value = {
        'message': {'content': "### Podsumowanie\nWszystko świetnie."}
    }
    
    # Aby raport zadziałał, potrzebujemy zadania ze statusem "done" lub zalogowanym czasem
    client.put(f"/tasks/{test_task['id']}", json={"title": "Ukończone Zadanie", "status": "done"}, headers=auth_headers)
    
    response = client.get("/tasks/generate-report", headers=auth_headers)
    assert response.status_code == 200
    assert "Podsumowanie" in response.json()["report"]


# --- POZOSTAŁE ENDPOINTY ---

def test_reset_schedule(auth_headers):
    response = client.post("/tasks/reset-schedule", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_delete_task(auth_headers, test_task):
    task_id = test_task["id"]
    response = client.delete(f"/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Upewniamy się, że zadanie zostało usunięte (powinno zwrócić 404)
    response_check = client.put(f"/tasks/{task_id}", json={"title": "Test"}, headers=auth_headers)
    assert response_check.status_code == 404