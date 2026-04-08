from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/purchase-orders", tags=["PurchaseOrders"])


@router.post("/")
def create_purchase_order(order: schemas.PurchaseOrderCreate, db: Session = Depends(get_db)):
    company = order.company
    input_code = order.product_code

    # 신품번 우선
    product = db.query(models.Product).filter(
        models.Product.new_code == input_code
    ).first()

    # 구품번도 허용
    if not product:
        product = db.query(models.Product).filter(
            models.Product.old_code == input_code
        ).first()

    if not product:
        raise Exception("존재하지 않는 품번입니다")

    real_code = product.new_code

    db_order = models.PurchaseOrder(
        product_code=real_code,
        quantity=order.quantity,
        company=company
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    return db_order


@router.get("/")
def get_purchase_orders(db: Session = Depends(get_db)):
    orders = db.query(models.PurchaseOrder).all()

    result = []

    for o in orders:
        product = db.query(models.Product).filter(
            models.Product.new_code == o.product_code
        ).first()

        result.append({
            "id": o.id,
            "product_code": o.product_code,
            "product_name": product.name if product else "",
            "quantity": o.quantity,
            "company": o.company,
            "status": o.status,
            "created_at": o.created_at
        })

    return result


@router.post("/complete/{order_id}")
def complete_purchase(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == order_id).first()

    if not order:
        raise Exception("주문 없음")

    if order.status == "DONE":
        raise Exception("이미 완료")

    order.status = "DONE"
    db.commit()

    return {"message": "완료"}


@router.post("/undo/{order_id}")
def undo_purchase(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == order_id).first()

    if not order:
        raise Exception("주문 없음")

    if order.status != "DONE":
        raise Exception("완료 상태만 취소 가능")

    order.status = "WAIT"
    db.commit()

    return {"message": "취소 완료"}


@router.delete("/{order_id}")
def delete_purchase(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == order_id).first()

    if not order:
        raise Exception("주문 없음")

    if order.status != "WAIT":
        raise Exception("대기 상태만 삭제 가능")

    db.delete(order)
    db.commit()

    return {"message": "삭제 완료"}
