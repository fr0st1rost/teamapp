from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Department
from app.schemas import UserResponse, DepartmentCreate, DepartmentResponse
from app.auth import get_admin_user, write_audit_log

router = APIRouter(
    prefix="/admin",
    tags=["Administracja (Users & Departments)"]
)

# ==========================
# Zarządzanie Działami
# ==========================
@router.post("/departments", response_model=DepartmentResponse)
def create_department(dept: DepartmentCreate, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    new_dept = Department(name=dept.name)
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    
    # ZAPIS DO AUDIT LOG (Dziennik Zdarzeń)
    write_audit_log(db, admin.id, "CREATE", "Department", new_dept.id, f"Utworzono dział: {new_dept.name}")
    
    return new_dept

@router.get("/departments", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    return db.query(Department).all()

# ==========================
# Zarządzanie Użytkownikami
# ==========================
@router.get("/users", response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    return db.query(User).all()

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
        
    db.delete(user_to_delete)
    db.commit()
    
    # ZAPIS DO AUDIT LOG (Dziennik Zdarzeń)
    write_audit_log(db, admin.id, "DELETE", "User", user_id, f"Usunięto użytkownika: {user_to_delete.email}")
    
    return {"message": "Użytkownik został usunięty"}