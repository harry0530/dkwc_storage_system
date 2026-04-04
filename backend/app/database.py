from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# =====================
# 🔥 DB URL (Render PostgreSQL)
# =====================
DATABASE_URL = os.getenv("DATABASE_URL")

# 로컬 테스트용 fallback (선택)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./inventory.db"

# =====================
# 🔥 PostgreSQL 대응
# =====================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# SQLite일 때만 옵션 적용
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# =====================
# DB 세션
# =====================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()