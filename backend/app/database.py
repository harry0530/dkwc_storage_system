from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "inventory.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_startup_migrations():
    """Apply lightweight SQLite schema fixes for local development."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "products" in tables:
        columns = {col["name"] for col in inspector.get_columns("products")}
        with engine.begin() as conn:
            if "min_stock" not in columns:
                conn.execute(
                    text("ALTER TABLE products ADD COLUMN min_stock INTEGER DEFAULT 0")
                )
