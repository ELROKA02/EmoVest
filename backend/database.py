from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Cargar .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("dataBase_url")

if not DATABASE_URL:
    raise RuntimeError(
        "Falta configurar DATABASE_URL o dataBase_url para conectar con la base de datos."
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
