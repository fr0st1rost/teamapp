import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import get_db
from app.models import Base
from app.main import app

# 1. Динамически берем URL базы из окружения Docker Compose
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://admin:N6N1DD8tUfNb397xoV6C@db:5432/teamflow"
)

# 2. Автоматически генерируем URL для тестовой базы
if DATABASE_URL.endswith("/teamflow"):
    TEST_DATABASE_URL = DATABASE_URL.replace("/teamflow", "/teamflow_test")
else:
    TEST_DATABASE_URL = f"{DATABASE_URL}_test"

def create_test_db_if_not_exists():
    # Подключаемся к основной базе в режиме AUTOCOMMIT для создания тестовой
    engine_admin = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    test_db_name = TEST_DATABASE_URL.split("/")[-1].split("?")[0]
    
    with engine_admin.connect() as conn:
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{test_db_name}'")
        ).fetchone()
        
        # Если базы teamflow_test нет — создаем ее
        if not result:
            conn.execute(text(f"CREATE DATABASE {test_db_name}"))

# Физически создаем базу перед началом тестов
create_test_db_if_not_exists()

# 3. Настраиваем движок на новую тестовую базу
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Фикстура для подготовки структуры таблиц"""
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    from app.models import Role
    # Создаем базовую роль, чтобы не падало на ForeignKey
    role = db.query(Role).filter(Role.id == 1).first()
    if not role:
        new_role = Role(id=1, name="admin")
        db.add(new_role)
        db.commit()
    db.close()

    yield  # Здесь pytest выполняет все тесты
    
    # Полностью очищаем базу после завершения тестов
    Base.metadata.drop_all(bind=engine)

# 4. Подменяем зависимость БД в самом FastAPI
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db