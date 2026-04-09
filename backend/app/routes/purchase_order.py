from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from datetime import datetime

router = APIRouter(prefix="/purchase-orders", tags=["PurchaseOrders"])

def resolve_product(db: Session, input_code: str):
    product = db.query(models.Product).filter(
        models.Product.new_code == input_code
    ).first()

    if not product:
        product = db.query(models.Product).filter(
            models.Product.old_code == input_code
        ).first()

    return product

def update_batch_status(db: Session, batch_id: int):
    if not batch_id:
        return

    items = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.batch_id == batch_id
    ).all()

    if not items:
        batch = db.query(models.PurchaseOrderBatch).filter(
            models.PurchaseOrderBatch.id == batch_id
        ).first()
        if batch:
            db.delete(batch)
            db.commit()
        return

    if all(i.status == "DONE" for i in items):
        status = "DONE"
    elif any((i.received_quantity or 0) > 0 for i in items):
        status = "PARTIAL"
    else:
        status = "WAIT"

    batch = db.query(models.PurchaseOrderBatch).filter(
        models.PurchaseOrderBatch.id == batch_id
    ).first()
    if batch:
        batch.status = status
        db.commit()


@router.get("/receipts")
def get_purchase_receipts(db: Session = Depends(get_db)):
    receipts = db.query(models.PurchaseOrderReceipt).all()
    return [
        {
            "id": r.id,
            "purchase_order_id": r.purchase_order_id,
            "quantity": r.quantity,
            "created_at": r.created_at
        }
        for r in receipts
    ]


@router.put("/receipts/{receipt_id}")
def update_receipt(receipt_id: int, data: schemas.PurchaseReceiptUpdate, db: Session = Depends(get_db)):
    receipt = db.query(models.PurchaseOrderReceipt).filter(
        models.PurchaseOrderReceipt.id == receipt_id
    ).first()
    if not receipt:
        raise Exception("입고 내역 없음")

    order = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.id == receipt.purchase_order_id
    ).first()
    if not order:
        raise Exception("발주 없음")

    new_qty = receipt.quantity
    if data.quantity is not None:
        new_qty = int(data.quantity)
        if new_qty <= 0:
            raise Exception("수량이 올바르지 않습니다")

    delta = new_qty - (receipt.quantity or 0)
    new_received = (order.received_quantity or 0) + delta

    if new_received < 0:
        raise Exception("입고 수량이 0보다 작아질 수 없습니다")
    if new_received > (order.quantity or 0):
        raise Exception("입고 수량이 주문 수량을 초과합니다")

    # 재고 반영
    if delta != 0:
        product = db.query(models.Product).filter(
            models.Product.new_code == order.product_code
        ).first()
        if product:
            product.quantity = (product.quantity or 0) + delta

        db.add(models.Transaction(
            product_code=order.product_code,
            quantity=abs(delta),
            type="IN" if delta > 0 else "OUT",
            reason="PURCHASE_EDIT"
        ))

    receipt.quantity = new_qty

    if data.created_at:
        try:
            receipt.created_at = datetime.fromisoformat(data.created_at.replace("Z", "+00:00"))
        except Exception:
            pass

    order.received_quantity = new_received
    if new_received == 0:
        order.status = "WAIT"
    elif new_received >= (order.quantity or 0):
        order.status = "DONE"
    else:
        order.status = "PARTIAL"

    db.commit()
    update_batch_status(db, order.batch_id)

    return {"message": "수정 완료"}


@router.delete("/receipts/{receipt_id}")
def delete_receipt(receipt_id: int, db: Session = Depends(get_db)):
    receipt = db.query(models.PurchaseOrderReceipt).filter(
        models.PurchaseOrderReceipt.id == receipt_id
    ).first()
    if not receipt:
        raise Exception("입고 내역 없음")

    order = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.id == receipt.purchase_order_id
    ).first()
    if not order:
        raise Exception("발주 없음")

    qty = receipt.quantity or 0
    new_received = (order.received_quantity or 0) - qty
    if new_received < 0:
        raise Exception("입고 수량이 0보다 작아질 수 없습니다")

    product = db.query(models.Product).filter(
        models.Product.new_code == order.product_code
    ).first()
    if product:
        product.quantity = (product.quantity or 0) - qty

    db.add(models.Transaction(
        product_code=order.product_code,
        quantity=qty,
        type="OUT",
        reason="PURCHASE_DELETE"
    ))

    order.received_quantity = new_received
    if new_received == 0:
        order.status = "WAIT"
    elif new_received >= (order.quantity or 0):
        order.status = "DONE"
    else:
        order.status = "PARTIAL"

    db.delete(receipt)
    db.commit()
    update_batch_status(db, order.batch_id)

    return {"message": "삭제 완료"}

@router.post("/batch")
def create_purchase_batch(data: schemas.PurchaseOrderBatchCreate, db: Session = Depends(get_db)):
    company = (data.company or "").strip()
    if not company:
        raise Exception("납품처가 필요합니다")

    if not data.items:
        raise Exception("발주 항목이 없습니다")

    batch = models.PurchaseOrderBatch(company=company)
    db.add(batch)
    db.commit()
    db.refresh(batch)

    created = []

    for item in data.items:
        input_code = item.product_code
        product = resolve_product(db, input_code)

        if not product:
            raise Exception("존재하지 않는 품번입니다")

        real_code = product.new_code

        db_order = models.PurchaseOrder(
            batch_id=batch.id,
            product_code=real_code,
            quantity=item.quantity,
            received_quantity=0,
            company=company
        )
        db.add(db_order)
        created.append(db_order)

    db.commit()
    return {"batch_id": batch.id, "count": len(created)}


@router.put("/{order_id}")
def update_purchase_order(order_id: int, data: schemas.PurchaseOrderUpdate, db: Session = Depends(get_db)):
    order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == order_id).first()
    if not order:
        raise Exception("발주 없음")

    new_company = (data.company or "").strip() if data.company is not None else order.company
    new_qty = order.quantity
    if data.quantity is not None:
        new_qty = int(data.quantity)
        if new_qty <= 0:
            raise Exception("수량이 올바르지 않습니다")
        if (order.received_quantity or 0) > new_qty:
            raise Exception("이미 입고된 수량보다 작게 수정할 수 없습니다")

    new_code = order.product_code
    if data.product_code:
        product = resolve_product(db, data.product_code)
        if not product:
            raise Exception("존재하지 않는 품번입니다")
        new_code = product.new_code

    # 제품 변경 시 재고 이동 (이미 입고된 수량 반영)
    if new_code != order.product_code and (order.received_quantity or 0) > 0:
        qty = order.received_quantity or 0
        old_product = db.query(models.Product).filter(
            models.Product.new_code == order.product_code
        ).first()
        new_product = db.query(models.Product).filter(
            models.Product.new_code == new_code
        ).first()

        if old_product:
            old_product.quantity = (old_product.quantity or 0) - qty
        if new_product:
            new_product.quantity = (new_product.quantity or 0) + qty

        db.add(models.Transaction(
            product_code=order.product_code,
            quantity=qty,
            type="OUT",
            reason="PURCHASE_EDIT"
        ))
        db.add(models.Transaction(
            product_code=new_code,
            quantity=qty,
            type="IN",
            reason="PURCHASE_EDIT"
        ))

    order.product_code = new_code
    order.quantity = new_qty
    order.company = new_company

    # 상태 재계산
    if (order.received_quantity or 0) == 0:
        order.status = "WAIT"
    elif (order.received_quantity or 0) >= new_qty:
        order.status = "DONE"
    else:
        order.status = "PARTIAL"

    # 배치 회사 동기화
    if order.batch_id and data.company is not None:
        batch = db.query(models.PurchaseOrderBatch).filter(
            models.PurchaseOrderBatch.id == order.batch_id
        ).first()
        if batch:
            batch.company = new_company
        db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.batch_id == order.batch_id
        ).update({"company": new_company})

    db.commit()
    update_batch_status(db, order.batch_id)

    return {"message": "수정 완료"}


@router.post("/")
def create_purchase_order(order: schemas.PurchaseOrderCreate, db: Session = Depends(get_db)):
    return create_purchase_batch(
        schemas.PurchaseOrderBatchCreate(
            company=order.company,
            items=[schemas.PurchaseOrderItemCreate(
                product_code=order.product_code,
                quantity=order.quantity
            )]
        ),
        db
    )


@router.get("/")
def get_purchase_orders(db: Session = Depends(get_db)):
    orders = db.query(models.PurchaseOrder).all()

    result = []

    for o in orders:
        product = db.query(models.Product).filter(
            models.Product.new_code == o.product_code
        ).first()
        batch = None
        if o.batch_id:
            batch = db.query(models.PurchaseOrderBatch).filter(
                models.PurchaseOrderBatch.id == o.batch_id
            ).first()

        result.append({
            "id": o.id,
            "batch_id": o.batch_id,
            "product_code": o.product_code,
            "product_name": product.name if product else "",
            "quantity": o.quantity,
            "received_quantity": o.received_quantity or 0,
            "company": o.company,
            "status": o.status,
            "created_at": o.created_at,
            "batch_created_at": batch.created_at if batch else o.created_at,
            "batch_company": batch.company if batch else o.company,
            "batch_status": batch.status if batch else o.status
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

    db.add(models.PurchaseOrderReceipt(
        purchase_order_id=order.id,
        quantity=qty
    ))

    db.add(models.Transaction(
        product_code=order.product_code,
        quantity=qty,
        type="IN",
        reason="PURCHASE_IN"
    ))

    db.commit()
    update_batch_status(db, order.batch_id)

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

    db.add(models.PurchaseOrderReceipt(
        purchase_order_id=order.id,
        quantity=remaining
    ))

    db.add(models.Transaction(
        product_code=order.product_code,
        quantity=remaining,
        type="IN",
        reason="PURCHASE_IN"
    ))

    db.commit()
    update_batch_status(db, order.batch_id)

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
    update_batch_status(db, order.batch_id)

    return {"message": "취소 완료"}


@router.delete("/{order_id}")
def delete_purchase(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == order_id).first()

    if not order:
        raise Exception("주문 없음")

    # 기존 입고 내역이 있으면 재고 되돌림 + 입고 내역 삭제
    receipts = db.query(models.PurchaseOrderReceipt).filter(
        models.PurchaseOrderReceipt.purchase_order_id == order.id
    ).all()
    if receipts:
        total = sum((r.quantity or 0) for r in receipts)
        product = db.query(models.Product).filter(
            models.Product.new_code == order.product_code
        ).first()
        if product:
            product.quantity = (product.quantity or 0) - total

        db.add(models.Transaction(
            product_code=order.product_code,
            quantity=total,
            type="OUT",
            reason="PURCHASE_DELETE"
        ))

        for r in receipts:
            db.delete(r)

    batch_id = order.batch_id
    db.delete(order)
    db.commit()
    update_batch_status(db, batch_id)

    return {"message": "삭제 완료"}
