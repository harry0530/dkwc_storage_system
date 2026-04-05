from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ✅ 재고 조회 (JOIN 버전)
@router.get("/")
def get_inventory(db: Session = Depends(get_db)):
    result = []

    inventory_list = db.query(models.Inventory).all()

    for inv in inventory_list:
        product = db.query(models.Product).filter(
            models.Product.code == inv.product_code
        ).first()

        result.append({
            "code": inv.product_code,
            "product_code": inv.product_code,
            "name": product.name if product else "",
            "location": product.location if product else "",
            "quantity": inv.quantity,
            "min_stock": product.min_stock if product else 0
        })

    return result


# ✅ 재고 입력 (복구됨 ⭐)
@router.post("/")
def create_inventory(inv: schemas.InventoryCreate, db: Session = Depends(get_db)):
    return crud.create_inventory(db, inv)


# ✅ 재고 수정 (수량 직접 수정)
@router.put("/{product_code}")
def update_inventory(product_code: str, data: dict, db: Session = Depends(get_db)):
    inv = db.query(models.Inventory).filter(
        models.Inventory.product_code == product_code
    ).first()

    if not inv:
        raise HTTPException(status_code=404, detail="재고 없음")

    if "quantity" in data:
        inv.quantity = data["quantity"]

    db.commit()

    return {"message": "수정 완료"}


# ✅ 재고 삭제 (목록에서 제거)
@router.delete("/{product_code}")
def delete_inventory(product_code: str, db: Session = Depends(get_db)):
    inv = db.query(models.Inventory).filter(
        models.Inventory.product_code == product_code
    ).first()

    if not inv:
        raise HTTPException(status_code=404, detail="재고 없음")

    db.delete(inv)
    db.commit()

    return {"message": "삭제 완료"}
