from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.models import Base
import app.models  # Чтобы Alembic прочел все классы

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata



def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    import os
    from sqlalchemy import engine_from_config, pool
    from app.database import SQLALCHEMY_DATABASE_URL
    
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = SQLALCHEMY_DATABASE_URL
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

    from sqlalchemy.orm import sessionmaker
    from app.models import Role, User
    from app.auth import get_password_hash

    Session = sessionmaker(bind=connectable)
    db = Session()
    try:
        role_admin = db.query(Role).filter(Role.name == "admin").first()
        if not role_admin:
            role_admin = Role(id=1, name="admin")
            db.add(role_admin)
            
        role_user = db.query(Role).filter(Role.name == "user").first()
        if not role_user:
            role_user = Role(id=2, name="user")
            db.add(role_user)
            
        db.commit()  

        mode = os.getenv("MOD", "PROD").upper()

        if mode == "PROD":
            admin_exists = db.query(User).filter(User.email == "admin@teamflow.pl").first()
            if not admin_exists:
                db.add(User(
                    email="admin@teamflow.pl",
                    hashed_password=get_password_hash("admin123"),
                    role_id=role_admin.id,
                    is_active=True
                ))
                db.commit()

        elif mode == "TEST":
            admin_exists = db.query(User).filter(User.email == "admin@teamflow.pl").first()
            if not admin_exists:
                db.add(User(
                    email="admin@teamflow.pl",
                    hashed_password=get_password_hash("admin123"),
                    role_id=role_admin.id,
                    is_active=True
                ))
            
            user_exists = db.query(User).filter(User.email == "tester@teamflow.pl").first()
            if not user_exists:
                db.add(User(
                    email="tester@teamflow.pl",
                    hashed_password=get_password_hash("user123"),
                    role_id=role_user.id,
                    is_active=True
                ))
            db.commit()  
            
    except Exception as e:
        db.rollback()
    finally:
        db.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
