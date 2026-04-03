from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("/")
def create_product(data: dict, db: Session = Depends(get_db)):
    product = models.Product(
        code=data["code"],
        name=data["name"],
        type=data["type"],
        location=data["location"],
        min_stock=data.get("min_stock", 0)  # ⭐ 핵심
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


@router.get("/")
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()