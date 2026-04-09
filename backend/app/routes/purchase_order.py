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
        received_quantity=0,
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
            "received_quantity": o.received_quantity or 0,
            "company": o.company,
            "status": o.status,
            "created_at": o.created_at
        })

    return result


@router.post("/receive/{order_id}")
def receive_purchase(order_id: int, data: schemas.PurchaseReceive, db: Session = Depends(get_db)):
    order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == order_id).first()

    if not order:
        raise Exception("주문 없음")

    if order.status == "DONE":
        raise Exception("이미 완료")

    qty = int(data.quantity or 0)
    if qty <= 0:
        raise Exception("입고 수량이 올바르지 않습니다")

    remaining = (order.quantity or 0) - (order.received_quantity or 0)
    if qty > remaining:
        raise Exception("입고 수량이 잔여 수량보다 많습니다")

    # 재고 반영
    product = db.query(models.Product).filter(
        models.Product.new_code == order.product_code
    ).first()
    if product:
        product.quantity = (product.quantity or 0) + qty

    order.received_quantity = (order.received_quantity or 0) + qty

    if order.received_quantity >= order.quantity:
        order.status = "DONE"
    else:
        order.status = "PARTIAL"

    db.add(models.Transaction(
        product_code=order.product_code,
        quantity=qty,
        type="IN",
        reason="PURCHASE_IN"
    ))

    db.commit()

    return {"message": "입고 완료", "received_quantity": order.received_quantity, "status": order.status}


@router.post("/receive-all/{order_id}")
def receive_all(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == order_id).first()

    if not order:
        raise Exception("주문 없음")

    if order.status == "DONE":
        raise Exception("이미 완료")

    remaining = (order.quantity or 0) - (order.received_quantity or 0)
    if remaining <= 0:
        raise Exception("잔여 수량 없음")

    # 재고 반영
    product = db.query(models.Product).filter(
        models.Product.new_code == order.product_code
    ).first()
    if product:
        product.quantity = (product.quantity or 0) + remaining

    order.received_quantity = (order.received_quantity or 0) + remaining
    order.status = "DONE"

    db.add(models.Transaction(
        product_code=order.product_code,
        quantity=remaining,
        type="IN",
        reason="PURCHASE_IN"
    ))

    db.commit()

    return {"message": "전체 입고 완료", "received_quantity": order.received_quantity, "status": order.status}


@router.post("/complete/{order_id}")
def complete_purchase(order_id: int, db: Session = Depends(get_db)):
    return receive_all(order_id, db)


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
