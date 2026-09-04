from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from .config import settings

if not settings.database_url.startswith(('postgresql://', 'postgresql+psycopg://')):
    raise RuntimeError('DATABASE_URL must point to PostgreSQL. SQLite is not supported for production.')

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def lock_calendar_day(db: Session, day) -> None:
    # Serialize booking/blocking operations for the same calendar day.
    db.execute(__import__('sqlalchemy').text('SELECT pg_advisory_xact_lock(hashtext(:day))'), {'day': day.isoformat()})
