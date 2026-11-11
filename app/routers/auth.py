from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Role
from app.schemas import UserCreate, UserResponse
from app.auth import get_password_hash, verify_password, create_access_token, timedelta, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["Autoryzacja"])

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Sprawdzamy, czy taki użytkownik już istnieje
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email jest już zarejestrowany")
        
    # Hashujemy hasło przed zapisaniem do bazy danych
    hashed_password = get_password_hash(user.password)
    
    # WAŻNE: dla celów testowych wymagamy podania role_id (np. 1). 
    # W rzeczywistym systemie rola jest przypisywana przez logikę biznesową.
    new_user = User(
        email=user.email, 
        hashed_password=hashed_password, 
        role_id=user.role_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Formularz OAuth2 używa pola 'username', my traktujemy je jako 'email'
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Nieprawidłowy email lub hasło")
        
    # Generujemy token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}