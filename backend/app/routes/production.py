from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

router = APIRouter(prefix="/production", tags=["Production"])


@router.get("/{product_id}")
def get_production(product_id: int, db: Session = Depends(get_db)):
    boms = db.query(models.BOM).filter(
        models.BOM.parent_product_id == product_id
    ).all()

    if not boms:
        return {"production_possible": 0}

    possible_list = []

    for bom in boms:
        inv = db.query(models.Inventory).filter(
            models.Inventory.product_id == bom.child_product_id
        ).first()

        if not inv or inv.quantity == 0:
            return {"production_possible": 0}

        possible = inv.quantity // bom.quantity
        possible_list.append(possible)

    return {"production_possible": min(possible_list)}