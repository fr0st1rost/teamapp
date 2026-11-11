import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Ładujemy zmienne środowiskowe z pliku .env
load_dotenv()

# Inicjalizujemy klienta Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def process_smart_inbox(text: str):
    # Używamy modelu Flash dla szybkości reakcji
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Prompt systemowy (instrukcja dla AI)
    prompt = f"""
    Jesteś profesjonalnym menedżerem IT. Twoim zadaniem jest dekompozycja nieustrukturyzowanego tekstu użytkownika na przejrzystą listę zadań.
    Odpowiedź zwróć ŚCIŚLE po polsku w formacie tablicy obiektów JSON. Każdy obiekt musi posiadać następujące klucze:
    - "title": krótkie i konkretne nazwanie zadania (string)
    - "description": szczegóły zadania, jeśli są zawarte w tekście (string)
    - "priority_ai": priorytet zadania (string, wybierz ściśle jeden z: "do_first", "schedule", "delegate", "eliminate", "do_now")
    - "estimated_time_minutes": szacowany czas wykonania w minutach według Twojej oceny (liczba całkowita)

    Tekst użytkownika: {text}
    """
    
    # Wysyłamy zapytanie, wymuszając format odpowiedzi JSON
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    
    # Przekształcamy ciąg znaków JSON z AI na listę słowników języka Python
    return json.loads(response.text)

def decompose_existing_task(title: str, description: str):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Jesteś profesjonalnym menedżerem IT. Twoim celem jest wzięcie dużego zadania i rozbicie go na 3-5 konkretnych, wykonalnych mikrokroków.
    
    Zadanie źródłowe: {title}
    Opis dodatkowy: {description}

    Odpowiedź zwróć ŚCIŚLE po polsku w formacie tablicy obiektów JSON. Każdy obiekt musi posiadać następujące klucze:
    - "title": krótkie nazwanie kroku (rozpocznij string od "[Krok]")
    - "description": szczegóły wykonania tego kroku
    - "priority_ai": priorytet (wybierz ściśle jeden z: "do_first", "schedule", "delegate", "do_now")
    - "estimated_time_minutes": szacowany czas wykonania w minutach (liczba całkowita)
    """
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    
    return json.loads(response.text)