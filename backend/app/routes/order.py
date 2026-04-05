from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/orders", tags=["Orders"])


# ⭐ 주문 생성 (alias + 우리품번 + 검증 포함)
@router.post("/")
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    company = order.company
    input_code = order.product_code

    # 1️⃣ alias 검사 (타회사 품번)
    alias = db.query(models.ProductAlias).filter(
        models.ProductAlias.company == company,
        models.ProductAlias.alias_code == input_code
    ).first()

    if alias:
        real_code = alias.product_code

    else:
        # 2️⃣ 우리 회사 품번 검사
        product = db.query(models.Product).filter(
            models.Product.code == input_code
        ).first()

        if product:
            real_code = input_code
        else:
            # 3️⃣ 잘못된 품번 차단
            raise Exception("존재하지 않는 품번입니다")

    db_order = models.Order(
        product_code=real_code,
        quantity=order.quantity,
        company=company
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    return db_order


# ⭐ 주문 조회 (제품명 포함)
@router.get("/")
def get_orders(db: Session = Depends(get_db)):
    orders = db.query(models.Order).all()

    result = []

    for o in orders:
        product = db.query(models.Product).filter(
            models.Product.code == o.product_code
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


# ⭐ 생산
@router.post("/produce/{order_id}")
def produce(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if order.status == "DONE":
        raise Exception("이미 완료")

    boms = db.query(models.BOM).filter(
        models.BOM.parent_code == order.product_code
    ).all()

    # 재고 체크
    for bom in boms:
        inv = db.query(models.Inventory).filter(
            models.Inventory.product_code == bom.child_code
        ).first()

        required = bom.quantity * order.quantity

        if not inv or inv.quantity < required:
            raise Exception("재고 부족")

    # 재고 차감
    for bom in boms:
        inv = db.query(models.Inventory).filter(
            models.Inventory.product_code == bom.child_code
        ).first()

        required = bom.quantity * order.quantity
        inv.quantity -= required

        db.add(models.Transaction(
            product_code=bom.child_code,
            quantity=required,
            type="OUT",
            reason="PRODUCTION"
        ))

    order.status = "DONE"
    db.commit()

    return {"message": "생산 완료"}


# ⭐ 생산 취소 (되돌리기)
@router.post("/undo/{order_id}")
def undo(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if order.status != "DONE":
        raise Exception("완료 상태만 취소 가능")

    boms = db.query(models.BOM).filter(
        models.BOM.parent_code == order.product_code
    ).all()

    # 재고 복구
    for bom in boms:
        inv = db.query(models.Inventory).filter(
            models.Inventory.product_code == bom.child_code
        ).first()

        restore = bom.quantity * order.quantity
        inv.quantity += restore

        db.add(models.Transaction(
            product_code=bom.child_code,
            quantity=restore,
            type="IN",
            reason="UNDO_PRODUCTION"
        ))

    order.status = "WAIT"
    db.commit()

    return {"message": "생산 취소 완료"}


# ⭐ 주문 삭제 (거부)
@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if not order:
        raise Exception("주문 없음")

    if order.status != "WAIT":
        raise Exception("대기 상태만 삭제 가능")

    db.delete(order)
    db.commit()

    return {"message": "삭제 완료"}
