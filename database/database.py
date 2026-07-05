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
    # PostgreSQL. pool_pre_ping tests each connection with a lightweight
    # query before handing it out and transparently reconnects if it's gone
    # stale - without it, the first request after the app or DB has been
    # idle for a while (common on Render) reuses a dead connection and blows
    # up with a generic 500 "Oops!" page that a refresh then silently fixes
    # (the retry gets a fresh connection). pool_recycle is a second safety
    # net for managed Postgres providers that close idle connections
    # server-side before the client even notices.
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=280)

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
