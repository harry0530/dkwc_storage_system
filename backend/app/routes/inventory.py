from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ???ш퀬 議고쉶 (JOIN 踰꾩쟾)
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
            "drawing_number": inv.drawing_number or "",
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


# ???ш퀬 ?낅젰 (蹂듦뎄??狩?
@router.post("/")
def create_inventory(inv: schemas.InventoryCreate, db: Session = Depends(get_db)):
    return crud.create_inventory(db, inv)


# ???ш퀬 ?섏젙 (?섎웾 吏곸젒 ?섏젙)
@router.put("/{product_code}")
def update_inventory(product_code: str, data: dict, db: Session = Depends(get_db)):
    inv = db.query(models.Product).filter(
        models.Product.new_code == product_code
    ).first()

    if not inv:
        raise HTTPException(status_code=404, detail="?ш퀬 ?놁쓬")

    if "quantity" in data:
        new_qty = data["quantity"]
        prev_qty = inv.quantity
        inv.quantity = new_qty

        diff = new_qty - prev_qty
        if diff != 0:
            reason = data.get("reason") or "?섎웾 蹂寃?"
            tx_type = "IN" if diff > 0 else "OUT"
            db.add(models.Transaction(
                product_code=inv.new_code,
                quantity=abs(diff),
                type=tx_type,
                reason=reason
            ))

    db.commit()

    return {"message": "?섏젙 ?꾨즺"}


# ???ш퀬 ??젣 (紐⑸줉?먯꽌 ?쒓굅)
@router.delete("/{product_code}")
def delete_inventory(product_code: str, db: Session = Depends(get_db)):
    inv = db.query(models.Product).filter(
        models.Product.new_code == product_code
    ).first()

    if not inv:
        raise HTTPException(status_code=404, detail="?ш퀬 ?놁쓬")

    db.delete(inv)
    db.commit()

    return {"message": "??젣 ?꾨즺"}
