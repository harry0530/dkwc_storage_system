from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
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


@router.delete("/{product_code}")
def delete_product(product_code: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(
        models.Product.code == product_code
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="제품 없음")

    # 제품 삭제 시 참조되는 기본 데이터 정리
    db.query(models.ProductAlias).filter(
        models.ProductAlias.product_code == product_code
    ).delete(synchronize_session=False)

    db.query(models.BOM).filter(
        or_(
            models.BOM.parent_code == product_code,
            models.BOM.child_code == product_code
        )
    ).delete(synchronize_session=False)

    db.query(models.Inventory).filter(
        models.Inventory.product_code == product_code
    ).delete(synchronize_session=False)

    db.delete(product)
    db.commit()

    return {"message": "삭제 완료"}


# ⭐ 제품 수정
@router.put("/{product_code}")
def update_product(product_code: str, data: dict, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(
        models.Product.code == product_code
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="제품 없음")

    product.name = data.get("name", product.name)
    product.type = data.get("type", product.type)
    product.location = data.get("location", product.location)
    product.min_stock = data.get("min_stock", product.min_stock)

    db.commit()
    return product
