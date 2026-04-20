from app import models


# =====================
# ?쒗뭹
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
        raise Exception("?놁쓬")

    db.delete(bom)
    db.commit()

    return {"message": "??젣 ?꾨즺"}


# =====================
# ?ш퀬
# =====================
def create_inventory(db, inv):
    existing = db.query(models.Product).filter(
        models.Product.new_code == inv.product_code
    ).first()

    if not existing:
        # old_code濡쒕룄 ?뺤씤
        existing = db.query(models.Product).filter(
            models.Product.old_code == inv.product_code
        ).first()

    if not existing:
        raise Exception("議댁옱?섏? ?딅뒗 ?덈쾲")

    existing.quantity += inv.quantity

    # 狩??낃퀬 濡쒓렇
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
# 二쇰Ц (?뵦 ?듭떖 ?섏젙??
# =====================
def create_order(db, order):

    input_code = order.product_code.strip()

    # 1截뤴깵 alias ???곕━ 肄붾뱶 蹂??    alias = db.query(models.ProductAlias).filter(
        models.ProductAlias.alias_code == input_code
    ).first()

    if alias:
        real_code = alias.product_code
    else:
        # 2截뤴깵 ?곕━ 肄붾뱶?몄? ?뺤씤
        product = db.query(models.Product).filter(
            models.Product.code == input_code
        ).first()

        if not product:
            raise Exception("議댁옱?섏? ?딅뒗 ?덈쾲")

        real_code = input_code

    # 狩???긽 ?곕━ 肄붾뱶濡????    db_order = models.Order(
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
# ?앹궛
# =====================
def run_production(db, order_id):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if order.status == "DONE":
        raise Exception("?대? ?꾨즺")

    # 狩??뱀떆 紐곕씪??怨듬갚 ?쒓굅
    order.product_code = order.product_code.strip()

    boms = db.query(models.BOM).filter(
        models.BOM.parent_code == order.product_code
    ).all()

    if not boms:
        raise Exception("BOM ?놁쓬")

    # 1截뤴깵 ?ш퀬 泥댄겕
    for bom in boms:
        inv = db.query(models.Inventory).filter(
            models.Inventory.product_code == bom.child_code
        ).first()

        required = bom.quantity * order.quantity

        if not inv or inv.quantity < required:
            raise Exception(f"{bom.child_code} ?ш퀬 遺議?)

    # 2截뤴깵 遺??李④컧 (OUT)
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

    # 3截뤴깵 ?꾩젣??利앷? (IN)
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

    # 4截뤴깵 ?곹깭 蹂寃?    order.status = "DONE"

    db.commit()


# =====================
# 濡쒓렇
# =====================
def get_transactions(db):
    return db.query(models.Transaction).all()
