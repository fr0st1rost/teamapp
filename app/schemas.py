from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models import TaskStatus, PriorityAI

# Schematy dla Użytkowników
class UserBase(BaseModel):
    email: EmailStr
    role_id: int
    department_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# Schematy dla Działów
class DepartmentBase(BaseModel):
    name: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: int

    class Config:
        from_attributes = True

#Schematy dla Komentarzy
#WAŻNE: Muszą być zdefiniowane przed TaskResponse,
#aby Pydantic mógł poprawnie powiązać typy.
class CommentBase(BaseModel):
    text: str

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    id: int
    task_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

#Schematy dla Zadań
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.INBOX
    priority_ai: Optional[PriorityAI] = None
    estimated_time_minutes: Optional[int] = 0
    logged_time_minutes: int = 0  # Licznik przepracowanego czasu
    deadline: Optional[datetime] = None
    project_id: Optional[int] = None

class TaskCreate(TaskBase):
    status: str = "inbox"
    priority_ai: Optional[str] = None
    estimated_time_minutes: int = 0
    logged_time_minutes: int = 0
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None

class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    user_id: int
    status: str
    priority_ai: Optional[str] = None
    estimated_time_minutes: int
    logged_time_minutes: int = 0
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    comments: List[CommentResponse] = [] # Zagnieżdżone komentarze

    class Config:
        from_attributes = True

#Inne schematy
class SmartInboxRequest(BaseModel):
    text: str