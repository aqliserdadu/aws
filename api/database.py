from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "aws_db.sqlite"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
