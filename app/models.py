from datetime import datetime
from enum import Enum
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Integer, Text, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class TaskStatus(str, Enum):
    INBOX = "inbox"           # Właśnie dodane, nieprzetworzone
    TODO = "todo"             # Do wykonania
    IN_PROGRESS = "in_progress"
    DONE = "done"

class PriorityAI(str, Enum):
    DO_FIRST = "do_first"     # Ważne i pilne
    SCHEDULE = "schedule"     # Ważne, ale niepilne
    DELEGATE = "delegate"     # Nieważne, ale pilne
    ELIMINATE = "eliminate"   # Nieważne i niepilne
    DO_NOW = "do_now"         # Zasada 2 minut (wykonaj natychmiast)

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # admin, manager, employee

    users: Mapped[List["User"]] = relationship(back_populates="role")

class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    users: Mapped[List["User"]] = relationship(back_populates="department")
    projects: Mapped[List["Project"]] = relationship(back_populates="department")

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"))

    role: Mapped["Role"] = relationship(back_populates="users")
    department: Mapped[Optional["Department"]] = relationship(back_populates="users")
    tasks: Mapped[List["Task"]] = relationship(back_populates="assignee")

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    
    department: Mapped["Department"] = relationship(back_populates="projects")
    tasks: Mapped[List["Task"]] = relationship(back_populates="project")

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Statusy i priorytety
    status: Mapped[TaskStatus] = mapped_column(String(50), default=TaskStatus.INBOX)
    priority_ai: Mapped[Optional[PriorityAI]] = mapped_column(String(50))

    # Metryki czasu
    estimated_time_minutes: Mapped[Optional[int]] = mapped_column(Integer) # Czas przewidziany przez AI
    logged_time_minutes: Mapped[int] = mapped_column(Integer, default=0)  # Czas rzeczywiście poświęcony
    comments: Mapped[list["Comment"]] = relationship(back_populates="task", cascade="all, delete-orphan")
   
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relacje
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id")) # Wykonawca

    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship(back_populates="tasks")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50), nullable=False) # CREATE, UPDATE, DELETE
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False) # Task, User, Department
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    details: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship()

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped["Task"] = relationship(back_populates="comments")
    user: Mapped["User"] = relationship()