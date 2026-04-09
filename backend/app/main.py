from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from sqlalchemy import text
import os

from app.routes import product, bom, inventory, transaction, order
from app.routes import purchase_order
import app.routes.company as company
from app.routes import log
from app.firebase_auth import verify_firebase_token


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.dkwc-manage.online",
        "https://dkwc-manage.online",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def ensure_company_email_column():
    db_url = str(engine.url)
    if db_url.startswith("postgresql"):
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS email TEXT")
            )
    else:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE companies ADD COLUMN email TEXT"))
        except Exception:
            pass


def ensure_purchase_order_columns():
    db_url = str(engine.url)
    if db_url.startswith("postgresql"):
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS received_quantity INTEGER DEFAULT 0")
            )
    else:
        # SQLite 등은 스키마 재생성 시 반영됨
        pass


if os.getenv("RESET_DB") == "1":
    db_url = str(engine.url)
    if db_url.startswith("postgresql"):
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    else:
        Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
ensure_company_email_column()
ensure_purchase_order_columns()

protected = [Depends(verify_firebase_token)]

app.include_router(product.router, dependencies=protected)
app.include_router(bom.router, dependencies=protected)
app.include_router(inventory.router, dependencies=protected)
app.include_router(transaction.router, dependencies=protected)
app.include_router(order.router, dependencies=protected)
app.include_router(purchase_order.router, dependencies=protected)
app.include_router(company.router, dependencies=protected)
app.include_router(log.router, dependencies=protected)

@app.get("/")
def health_check():
    return {"status": "ok"}
