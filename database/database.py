from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'sqlite:///./menu_planner.db'  # Default to SQLite for local dev if no env var
)

# Use StaticPool for SQLite (thread-safe for development)
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool
    )
else:
    # PostgreSQL
    engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Create a singleton db instance for Flask integration
class Database:
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        self.Base = Base

    def get_session(self):
        return SessionLocal()

    def create_all(self):
        self.Base.metadata.create_all(bind=self.engine)

    def drop_all(self):
        self.Base.metadata.drop_all(bind=self.engine)

db = Database()

def init_db():
    """Initialize database (create all tables)."""
    db.create_all()
