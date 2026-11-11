from fastapi import APIRouter, Depends
from httpcore import request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task
from app.schemas import TaskCreate, TaskResponse
from typing import List
from fastapi import HTTPException
from app.auth import get_current_user
from app.models import User, Comment
from app.ai_engine import process_smart_inbox, decompose_existing_task
from app.schemas import SmartInboxRequest, CommentCreate, CommentResponse
from pydantic import BaseModel
import ollama
import json
import re
import os
from datetime import datetime, timedelta

# Tworzymy router z prefiksem /tasks
router = APIRouter(
    prefix="/tasks",
    tags=["Zadania (Tasks)"]
)

class RescheduleRequest(BaseModel):
    days_range: int  # 1, 3, 7 dni
    productivity_mode: str  # "morning" (produktywny rano) lub "evening" (wieczorem)

@router.post("/smart-inbox", response_model=List[TaskResponse])
def create_tasks_via_ai(request: SmartInboxRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # 1. Wysyłamy surowy tekst do Gemini
        ai_tasks_data = process_smart_inbox(request.text)
        
        created_tasks = []
        # 2. Przetwarzamy odpowiedź od AI i zapisujemy w naszej bazie
        for task_data in ai_tasks_data:
            new_task = Task(
                title=task_data.get("title", "Bez nazwy"),
                description=task_data.get("description", ""),
                priority_ai=task_data.get("priority_ai", "schedule"),
                estimated_time_minutes=task_data.get("estimated_time_minutes", 0),
                status="inbox",
                user_id=current_user.id
            )
            db.add(new_task)
            created_tasks.append(new_task)
            
        db.commit()
        
        # Odświeżamy obiekty, aby pobrać ich ID z bazy
        for t in created_tasks:
            db.refresh(t)
            
        return created_tasks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd przetwarzania AI: {str(e)}")
    
# Endpoint do dekompozycji konkretnego zadania
@router.post("/{task_id}/decompose", response_model=List[TaskResponse])
def decompose_task_endpoint(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Szukamy oryginalnego zadania w bazie i sprawdzamy uprawnienia
    db_task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    
    if not db_task:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania lub brak uprawnień")

    try:
        # 2. Wysyłamy dane zadania do sieci neuronowej
        subtasks_data = decompose_existing_task(db_task.title, db_task.description or "")
        
        created_subtasks = []
        # 3. Zapisujemy otrzymane mikro-kroki jako nowe zadania
        for item in subtasks_data:
            new_task = Task(
                title=item.get("title", "Bez nazwy"),
                # Programowo dodajemy link do oryginalnego zadania w opisie
                description=f'Odnosi się do zadania: "{db_task.title}". ' + item.get("description", ""),
                priority_ai=item.get("priority_ai", "schedule"),
                estimated_time_minutes=item.get("estimated_time_minutes", 0),
                status="inbox",
                user_id=current_user.id
            )
            db.add(new_task)
            created_subtasks.append(new_task)
            
        db.commit()
        
        for t in created_subtasks:
            db.refresh(t)
            
        return created_subtasks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd dekompozycji AI: {str(e)}")
    

# Endpoint do tworzenia nowego zadania (żądanie POST)
@router.post("/", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Rozpakowujemy dane ze schematu Pydantic i tworzymy obiekt bazy danych
    new_task = Task(**task.model_dump(), user_id=current_user.id)
    
    # Dodajemy do sesji, zapisujemy w bazie i odświeżamy obiekt (aby uzyskać wygenerowane ID)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return new_task

@router.get("/", response_model=List[TaskResponse])
def get_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # DODANO FILTR: zwracamy tylko zadania bieżącego użytkownika
    tasks = db.query(Task).filter(Task.user_id == current_user.id).offset(skip).limit(limit).all()
    return tasks

# Endpoint do aktualizacji zadania (żądanie PUT)
@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_update: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # DODANO FILTR: szukamy zadania po ID + sprawdzamy, czy należy do użytkownika
    db_task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    
    if db_task is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania lub brak uprawnień do edycji")
    
    # Aktualizujemy pola
    for key, value in task_update.model_dump().items():
        setattr(db_task, key, value)
        
    db.commit()
    db.refresh(db_task)
    return db_task

@router.post("/{task_id}/comments", response_model=CommentResponse)
def add_comment(task_id: int, comment: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Sprawdzamy, czy takie zadanie istnieje
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania")

    new_comment = Comment(
        text=comment.text,
        task_id=task_id,
        user_id=current_user.id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    
    return new_comment

# Endpoint do usuwania zadania (żądanie DELETE)
@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Po prostu szukamy zadania po ID
    db_task = db.query(Task).filter(Task.id == task_id).first()
    
    if db_task is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania")
        
    # 2. WERYFIKACJA UPRAWNIEŃ (Security): 
    # Zezwalamy na usunięcie, jeśli użytkownik jest właścicielem zadania LUB jego rola to "admin"
    if db_task.user_id != current_user.id and current_user.role.name != "admin":
        # 403 Forbidden — serwer zrozumiał żądanie, ale odmawia wykonania z powodu braku uprawnień
        raise HTTPException(status_code=403, detail="Brak uprawnień do usunięcia cudzego zadania")
        
    # 3. Usuwamy i zapisujemy zmiany
    db.delete(db_task)
    db.commit()
    
    return {"message": f"Zadanie o ID {task_id} zostało pomyślnie usunięte"}

@router.post("/reschedule-ai")
def reschedule_tasks_with_ai(
    request: RescheduleRequest,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    tasks = db.query(Task).filter(Task.user_id == current_user.id, Task.status != "done").all()
    if not tasks:
        raise HTTPException(status_code=400, detail="Brak zadań do zaplanowania.")

    tasks_pool = [{
        "id": t.id,
        "title": t.title,
        "description": t.description or "",
        "priority": t.priority_ai or "inbox"
    } for t in tasks]

    # Dynamicznie adaptujemy prompt pod biorytmy użytkownika
    prod_instruction = ""
    if request.productivity_mode == "morning":
        prod_instruction = "Najważniejsze i najtrudniejsze zadania zaplanuj w pierwszej połowie dnia (09:00 - 13:00)."
    elif request.productivity_mode == "evening":
        prod_instruction = "Skomplikowane zadania techniczne zaplanuj w godzinach 14:00 - 18:00."

    # RYGORYSTYCZNY PROMPT (Zwrócono przykład, aby model nie halucynował)
    system_prompt = f"""
    Jesteś algorytmem AI optymalizującym harmonogram pracy na najbliższe {request.days_range} dni.
    Twoim zadaniem jest posortowanie listy zadań w taki sposób, aby zminimalizować przełączanie kontekstu.
    
    PREFERENCJE UŻYTKOWNIKA:
    {prod_instruction}

    ZADANIA DO POSORTOWANIA:
    {json.dumps(tasks_pool, ensure_ascii=False)}

    BARDZO WAŻNE INSTRUKCJE FORMATOWANIA:
    1. MUSISZ zwrócić swoje myśli wyłącznie w tagach <mysli> i </mysli>. Nie używaj Markdown.
    2. Bezpośrednio pod tagami MUSISZ zwrócić PŁASKĄ tablicę JSON zawierającą same liczby (ID zadań).
    3. ZABRONIONE jest tworzenie obiektów JSON w tablicy (nie pisz "id": ...).
    4. ZABRONIONE jest dodawanie jakiegokolwiek tekstu po tablicy JSON.

    SZABLON ODPOWIEDZI (Zwróć dokładnie tę strukturę, wstawiając PRAWDZIWE ID z listy zadań):
    <mysli>
    Twoje logiczne wyjaśnienie dlaczego tak ułożono zadania...
    </mysli>
    [ID_ZADANIA_1, ID_ZADANIA_2, ID_ZADANIA_3]
    """

    try:
        client = ollama.Client(host=os.getenv("OLLAMA_HOST_URL", "http://127.0.0.1:11434")) 
        response = client.chat(model='llama3', messages=[{'role': 'user', 'content': system_prompt}])
        raw_content = response['message']['content'].strip()

        thoughts_match = re.search(r'<mysli>(.*?)</mysli>', raw_content, re.DOTALL | re.IGNORECASE)
        ai_thoughts = thoughts_match.group(1).strip() if thoughts_match else "Zoptymalizowano kolejność."
        
        match = re.search(r'\[\s*\d+\s*(?:\,\s*\d+\s*)*\]', raw_content)
        if not match:
            # Wypisujemy w konsoli rzeczywistą odpowiedź modelu, aby zrozumieć, gdzie popełnił błąd
            print(f"\n❌ BŁĄD PARSOWANIA AI. Surowa odpowiedź modelu:\n{raw_content}\n")
            raise ValueError("Model nie zwrócił tablicy JSON.")
        
        ordered_ids = json.loads(match.group(0))

        # DETERMINISTYCZNE PLANOWANIE
        start_pointer = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        if start_pointer.weekday() == 5: start_pointer += timedelta(days=2)
        elif start_pointer.weekday() == 6: start_pointer += timedelta(days=1)

        end_boundary = start_pointer + timedelta(days=request.days_range)

        for task_id in ordered_ids:
            task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
            if not task or start_pointer >= end_boundary:
                continue

            duration = task.estimated_time_minutes if task.estimated_time_minutes > 0 else 60
            
            if start_pointer.hour >= 18 or (start_pointer + timedelta(minutes=duration)).hour > 18:
                start_pointer = start_pointer.replace(hour=9, minute=0) + timedelta(days=1)
                if start_pointer.weekday() == 5: start_pointer += timedelta(days=2)
                if start_pointer.weekday() == 6: start_pointer += timedelta(days=1)

            task.scheduled_start = start_pointer
            task.scheduled_end = start_pointer + timedelta(minutes=duration)
            start_pointer = task.scheduled_end + timedelta(minutes=15)

        db.commit()
        return {"status": "success", "ai_thoughts": ai_thoughts}
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ KRYTYCZNY BŁĄD ENDPOINTU: {str(e)}\n")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-schedule")
def reset_calendar_schedule(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # Po prostu resetujemy daty planowania na NULL dla wszystkich aktywnych zadań użytkownika
        db.query(Task).filter(
            Task.user_id == current_user.id
        ).update({Task.scheduled_start: None, Task.scheduled_end: None}, synchronize_session=False)
        
        db.commit()
        return {"status": "success", "message": "Kalendarz został wyczyszczony."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd resetowania: {str(e)}")
    
@router.get("/generate-report")
def generate_weekly_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Pobieramy zakończone zadania ORAZ zadania, dla których zalogowano czas
    analyzed_tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        (Task.status == "done") | (Task.logged_time_minutes > 0)
    ).all()

    if not analyzed_tasks:
        raise HTTPException(status_code=400, detail="Brak danych do analizy. Ukończ kilka zadań lub zaloguj czas.")

    # 2. Tworzymy kontekst, obowiązkowo przekazując różnicę w czasie
    tasks_text = ""
    total_estimated = 0
    total_logged = 0

    for t in analyzed_tasks:
        est = t.estimated_time_minutes or 0
        log = t.logged_time_minutes or 0
        total_estimated += est
        total_logged += log
        
        comments_str = " ".join([c.text for c in t.comments]) if t.comments else "Brak"
        tasks_text += f"- Zadanie: '{t.title}'. Planowano: {est} min, Faktycznie spędzono: {log} min. Notatki: {comments_str}.\n"

    # 3. Inżynieryjny Prompt dla analityki
    system_prompt = f"""
    Jesteś analitykiem produktywności i ekspertem DevOps. 
    Wygeneruj Raport Efektywności (Analiza powykonawcza) na podstawie poniższych danych.

    DANE OGÓLNE:
    Suma zaplanowanego czasu: {total_estimated} minut.
    Suma rzeczywiście spędzonego czasu: {total_logged} minut.

    SUROWE DANE O ZADANIACH:
    {tasks_text}

    WYMAGANA STRUKTURA RAPORTU (w formacie Markdown):
    ### Podsumowanie realizacji planów
    (Krótko opisz, co udało się osiągnąć i jak wygląda ogólny bilans czasu)

    ### Złodzieje Czasu (Time Thieves)
    (Wskaż konkretne zadania, które zajęły znacznie więcej czasu niż planowano. Przeanalizuj dlaczego tak się stało - np. brak specyfikacji, problemy techniczne).

    ### Rekomendacje dla inżyniera IT
    (Zaproponuj 2-3 konkretne, motywujące porady, jak uniknąć utraty czasu w przyszłym tygodniu).

    Pisz profesjonalnym, motywującym tonem WYŁĄCZNIE w języku polskim. Nie używaj języka angielskiego.
    """

    try:
        client = ollama.Client(host=os.getenv("OLLAMA_HOST_URL", "http://127.0.0.1:11434")) 
        response = client.chat(model='llama3', messages=[{'role': 'user', 'content': system_prompt}])
        
        return {"report": response['message']['content']}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd analizy AI: {str(e)}")