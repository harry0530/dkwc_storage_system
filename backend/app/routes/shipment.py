from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

router = APIRouter(prefix="/shipment", tags=["Shipment"])


@router.post("/{product_code}")
def ship(product_code: str, quantity: int, db: Session = Depends(get_db)):
    inv = db.query(models.Inventory).filter(
        models.Inventory.product_code == product_code
    ).first()

    if not inv or inv.quantity < quantity:
        raise HTTPException(status_code=400, detail="재고 부족")

    inv.quantity -= quantity

    db.add(models.Transaction(
        product_code=product_code,
        quantity=quantity,
        type="OUT",
        reason="SHIPMENT"
    ))

    db.commit()

    return {"message": "출고 완료"}