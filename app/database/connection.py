"""Database connection and session management."""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Database file in project root
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "synapsecli.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine with check_same_thread=False for development
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Session:
    """Context manager for safe database session handling."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables() -> None:
    """Create all tables on startup."""
    from app.database.models import Base
    Base.metadata.create_all(bind=engine)
