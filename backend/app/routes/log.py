from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/")
def get_logs(db: Session = Depends(get_db)):

    transactions = db.query(models.Transaction).all()
    orders = db.query(models.Order).all()

    logs = []

    for t in transactions:
        logs.append({
            "time": t.created_at,
            "type": "재고",
            "product": t.product_code,
            "quantity": t.quantity,
            "company": "",
            "desc": t.reason
        })

    for o in orders:
        logs.append({
            "time": o.created_at,
            "type": "주문",
            "product": o.product_code,
            "quantity": o.quantity,
            "company": o.company,
            "desc": o.status
        })

    logs.sort(key=lambda x: x["time"], reverse=True)

    return logs