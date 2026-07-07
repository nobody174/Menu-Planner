from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./menu_planner.db",  # Default to SQLite for local dev if no env var
)

# Concurrent requests against the SQLite dev database used to corrupt
# cursor state (confirmed: intermittent sqlite3.InterfaceError,
# sqlite3.OperationalError, and IndexError from two overlapping requests
# to /api/reroll-recipe or /api/swap-recipe - a double-click, a slow
# retry, or just a browser's normal multiple simultaneous connections per
# page load). Two things were tried and reverted before this: a global
# lock around connection checkout (deadlocked the whole app if a request
# died mid-flight without releasing it), and threaded=False on the Flask
# dev server (choked on a real browser's several simultaneous
# connections per page, since only one could ever be served at a time).
#
# The actual fix: SQLite's own WAL (Write-Ahead Logging) journal mode,
# which is specifically designed for "multiple readers + one writer"
# concurrent access - no custom locking needed, and it's the standard
# fix for exactly this Flask+SQLite combination. WAL only works with
# genuinely separate connections per thread, so this also switches off
# StaticPool (which forced every thread onto one shared connection,
# defeating WAL's purpose) back to SQLAlchemy's normal per-thread pool.
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_wal_mode(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

else:
    # PostgreSQL. pool_pre_ping tests each connection with a lightweight
    # query before handing it out and transparently reconnects if it's gone
    # stale - without it, the first request after the app or DB has been
    # idle for a while (common on Render) reuses a dead connection and blows
    # up with a generic 500 "Oops!" page that a refresh then silently fixes
    # (the retry gets a fresh connection). pool_recycle is a second safety
    # net for managed Postgres providers that close idle connections
    # server-side before the client even notices.
    engine = create_engine(
        DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=280
    )

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
