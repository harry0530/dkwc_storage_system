from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine

from app.routes import product, bom, inventory, transaction, production, order, shipment, product_alias
import app.routes.company as company
from app.routes import log


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(product.router)
app.include_router(bom.router)
app.include_router(inventory.router)
app.include_router(transaction.router)
app.include_router(production.router)
app.include_router(order.router)
app.include_router(shipment.router)
app.include_router(product_alias.router)
app.include_router(company.router)
app.include_router(log.router)

@app.get("/")
def health_check():
    return {"status": "ok"}
