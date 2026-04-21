from app import models


def update_bom(db, bom_id, data):
    bom = db.query(models.BOM).filter(models.BOM.id == bom_id).first()

    if not bom:
        raise Exception("없음")

    child_code = (data.child_code or "").strip()
    if not child_code:
        raise Exception("부품 품번이 필요합니다")

    quantity = int(data.quantity or 0)
    if quantity <= 0:
        raise Exception("수량은 1 이상이어야 합니다")

    duplicate = db.query(models.BOM).filter(
        models.BOM.parent_code == bom.parent_code,
        models.BOM.child_code == child_code,
        models.BOM.id != bom_id
    ).first()
    if duplicate:
        raise Exception("이미 같은 BOM 항목이 있습니다")

    bom.child_code = child_code
    bom.quantity = quantity
    db.commit()
    db.refresh(bom)

    return bom


# =====================
# 제품
# =====================
def create_product(db, product):
    data = product.dict()
    db_product = models.Product(
        old_code=data.get("old_code") or "",
        new_code=data.get("code"),
        drawing_number=data.get("drawing_number") or "",
        name=data.get("name"),
        type=data.get("type"),
        material=data.get("material") or "",
        spec=data.get("spec") or "",
        quantity=data.get("quantity") or 0,
        min_stock=data.get("min_stock") or 0,
        location=data.get("location") or "",
        supplier_company_id=data.get("supplier_company_id")
    )
    db.add(db_product)
    db.commit()

    return db_product


def get_products(db):
    return db.query(models.Product).all()


# =====================
# BOM
# =====================
def create_bom(db, bom):
    db_bom = models.BOM(**bom.dict())
    db.add(db_bom)
    db.commit()
    return db_bom


def get_all_bom(db):
    return db.query(models.BOM).all()


def get_bom_by_product(db, product_code):
    return db.query(models.BOM).filter(
        models.BOM.parent_code == product_code
    ).all()


def delete_bom(db, bom_id):
    bom = db.query(models.BOM).filter(models.BOM.id == bom_id).first()

    if not bom:
        raise Exception("없음")

    db.delete(bom)
    db.commit()

    return {"message": "삭제 완료"}


# =====================
# 재고
# =====================
def create_inventory(db, inv):
    existing = db.query(models.Product).filter(
        models.Product.new_code == inv.product_code
    ).first()

    if not existing:
        # old_code로도 확인
        existing = db.query(models.Product).filter(
            models.Product.old_code == inv.product_code
        ).first()

    if not existing:
        raise Exception("존재하지 않는 품번")

    existing.quantity += inv.quantity

    # ⭐ 입고 로그
    db.add(models.Transaction(
        product_code=existing.new_code,
        quantity=inv.quantity,
        type="IN",
        reason=inv.reason or "STOCK_IN"
    ))

    db.commit()


def get_inventory(db):
    return db.query(models.Product).filter(models.Product.type == "PART").all()


# =====================
# 주문 (🔥 핵심 수정됨)
# =====================
def create_order(db, order):

    input_code = order.product_code.strip()

    # 1️⃣ alias → 우리 코드 변환
    alias = db.query(models.ProductAlias).filter(
        models.ProductAlias.alias_code == input_code
    ).first()

    if alias:
        real_code = alias.product_code
    else:
        # 2️⃣ 우리 코드인지 확인
        product = db.query(models.Product).filter(
            models.Product.code == input_code
        ).first()

        if not product:
            raise Exception("존재하지 않는 품번")

        real_code = input_code

    # ⭐ 항상 우리 코드로 저장
    db_order = models.Order(
        product_code=real_code,
        quantity=order.quantity,
        company=order.company
    )

    db.add(db_order)
    db.commit()

    return db_order


def get_orders(db):
    return db.query(models.Order).all()


# =====================
# 생산
# =====================
def run_production(db, order_id):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if order.status == "DONE":
        raise Exception("이미 완료")

    # ⭐ 혹시 몰라서 공백 제거
    order.product_code = order.product_code.strip()

    boms = db.query(models.BOM).filter(
        models.BOM.parent_code == order.product_code
    ).all()

    if not boms:
        raise Exception("BOM 없음")

    # 1️⃣ 재고 체크
    for bom in boms:
        inv = db.query(models.Inventory).filter(
            models.Inventory.product_code == bom.child_code
        ).first()

        required = bom.quantity * order.quantity

        if not inv or inv.quantity < required:
            raise Exception(f"{bom.child_code} 재고 부족")

    # 2️⃣ 부품 차감 (OUT)
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

    # 3️⃣ 완제품 증가 (IN)
    finished_inv = db.query(models.Inventory).filter(
        models.Inventory.product_code == order.product_code
    ).first()

    if not finished_inv:
        finished_inv = models.Inventory(
            product_code=order.product_code,
            quantity=0
        )
        db.add(finished_inv)

    finished_inv.quantity += order.quantity

    db.add(models.Transaction(
        product_code=order.product_code,
        quantity=order.quantity,
        type="IN",
        reason="PRODUCTION"
    ))

    # 4️⃣ 상태 변경
    order.status = "DONE"

    db.commit()


# =====================
# 로그
# =====================
def get_transactions(db):
    return db.query(models.Transaction).all()
