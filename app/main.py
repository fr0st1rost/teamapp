import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importowanie ruterów aplikacji
from app.routers import tasks, auth, admin

# Konfiguracja rejestrowania zdarzeń (logowania) w konsoli Docker
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TeamFlow")

# Definicja menedżera cyklu życia aplikacji (Lifespan) do automatyzacji bazy danych
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Sprawdzanie i automatyczne nakładanie migracji bazy danych... ===")
    try:
        from alembic.config import Config
        from alembic import command
        import os

        # Dynamiczne określanie ścieżki do pliku konfiguracji alembic.ini
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))
        
        # Uruchomienie programowej aktualizacji struktury bazy danych do najnowszej wersji (head)
        command.upgrade(alembic_cfg, "head")
        logger.info("=== Struktura bazy danych została pomyślnie zsynchronizowana. ===")
    except Exception as e:
        logger.error(f"[Krytyczny błąd automatyzacji bazy danych]: {e}")
    
    yield  # Serwer FastAPI rozpoczyna przyjmowanie żądań HTTP
    
    logger.info("=== Zamykanie aplikacji systemowej TeamFlow ===")

# Inicjalizacja instancji aplikacji FastAPI
app = FastAPI(
    title="AI TeamFlow Orchestrator",
    description="Interfejs API dla systemu zarządzania procesami roboczymi z technologią sztucznej inteligencji",
    version="1.0.0",
    lifespan=lifespan
)

# Konfiguracja polityki CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(tasks.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")