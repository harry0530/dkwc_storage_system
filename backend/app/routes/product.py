from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/products", tags=["Products"])


# 🔥 핵심 수정 부분
@router.post("/")
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    
    db_product = models.Product(
        code=product.code,
        name=product.name,
        type=product.type,
        location=product.location,
        min_stock=product.min_stock
    )

    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return db_product


@router.get("/")
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()