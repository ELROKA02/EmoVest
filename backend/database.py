from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_PATH, SQLITE_BUSY_TIMEOUT_MS


def sqlite_url(database_path: str | Path) -> URL:
    path = Path(database_path).expanduser()
    if not path.is_absolute():
        raise RuntimeError("La base de datos de escritorio requiere una ruta absoluta.")
    return URL.create("sqlite+pysqlite", database=str(path.resolve()))


def create_desktop_engine(
    database_path: str | Path = DATABASE_PATH,
    *,
    busy_timeout_ms: int = SQLITE_BUSY_TIMEOUT_MS,
) -> Engine:
    path = Path(database_path).expanduser()
    if not path.is_absolute():
        raise RuntimeError("La base de datos de escritorio requiere una ruta absoluta.")
    path.parent.mkdir(parents=True, exist_ok=True)

    desktop_engine = create_engine(
        sqlite_url(path),
        connect_args={
            "check_same_thread": False,
            "timeout": busy_timeout_ms / 1000,
        },
        pool_pre_ping=True,
    )

    @event.listens_for(desktop_engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()

    return desktop_engine


DATABASE_URL = sqlite_url(DATABASE_PATH)
engine = create_desktop_engine()
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
