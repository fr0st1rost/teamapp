import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ciąg połączeniowy do kontenera PostgreSQL
# Format: postgresql://użytkownik:hasło@host:port/nazwa_bazy
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://admin:N6N1DD8tUfNb397xoV6C@192.168.94.141:5432/teamflow"
)

# Tworzymy silnik bazy danych (engine)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Tworzymy fabrykę sesji (SessionLocal)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Zależność (dependency) dla FastAPI, używana w routerach do obsługi sesji
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()