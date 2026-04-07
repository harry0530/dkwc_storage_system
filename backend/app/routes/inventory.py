from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ✅ 재고 조회 (JOIN 버전)
@router.get("/")
def get_inventory(db: Session = Depends(get_db)):
    result = []

    inventory_list = db.query(models.Product).filter(
        models.Product.type == "PART"
    ).all()

    for inv in inventory_list:
        result.append({
            "code": inv.new_code,
            "product_code": inv.new_code,
            "old_code": inv.old_code,
            "new_code": inv.new_code,
            "name": inv.name or "",
            "material": inv.material or "",
            "spec": inv.spec or "",
            "type": inv.type,
            "location": inv.location or "",
            "quantity": inv.quantity,
            "min_stock": inv.min_stock,
            "supplier_company_id": inv.supplier_company_id
        })

    return result


# ✅ 재고 입력 (복구됨 ⭐)
@router.post("/")
def create_inventory(inv: schemas.InventoryCreate, db: Session = Depends(get_db)):
    return crud.create_inventory(db, inv)


# ✅ 재고 수정 (수량 직접 수정)
@router.put("/{product_code}")
def update_inventory(product_code: str, data: dict, db: Session = Depends(get_db)):
    inv = db.query(models.Product).filter(
        models.Product.new_code == product_code
    ).first()

    if not inv:
        raise HTTPException(status_code=404, detail="재고 없음")

    if "quantity" in data:
        new_qty = data["quantity"]
        prev_qty = inv.quantity
        inv.quantity = new_qty

        diff = new_qty - prev_qty
        if diff != 0:
            reason = data.get("reason") or "수량 변경"
            tx_type = "IN" if diff > 0 else "OUT"
            db.add(models.Transaction(
                product_code=inv.new_code,
                quantity=abs(diff),
                type=tx_type,
                reason=reason
            ))

    db.commit()

    return {"message": "수정 완료"}


# ✅ 재고 삭제 (목록에서 제거)
@router.delete("/{product_code}")
def delete_inventory(product_code: str, db: Session = Depends(get_db)):
    inv = db.query(models.Product).filter(
        models.Product.new_code == product_code
    ).first()

    if not inv:
        raise HTTPException(status_code=404, detail="재고 없음")

    db.delete(inv)
    db.commit()

    return {"message": "삭제 완료"}
