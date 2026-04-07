from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
import os

from app.routes import product, bom, inventory, transaction, order
import app.routes.company as company
from app.routes import log
from app.firebase_auth import verify_firebase_token


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.getenv("RESET_DB") == "1":
    Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

protected = [Depends(verify_firebase_token)]

app.include_router(product.router, dependencies=protected)
app.include_router(bom.router, dependencies=protected)
app.include_router(inventory.router, dependencies=protected)
app.include_router(transaction.router, dependencies=protected)
app.include_router(order.router, dependencies=protected)
app.include_router(company.router, dependencies=protected)
app.include_router(log.router, dependencies=protected)

@app.get("/")
def health_check():
    return {"status": "ok"}
