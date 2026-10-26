from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from app.config.settings import settings

database_url = settings.get_database_url()

# Provide appropriate connection arguments depending on dialect
connect_args = {}
if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif "postgres" in database_url:
    connect_args["connect_timeout"] = 15

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection(db: Session = None) -> bool:
    """Executes a lightweight query to check database connectivity."""
    try:
        if db is not None:
            db.execute(text("SELECT 1"))
            return True
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False
