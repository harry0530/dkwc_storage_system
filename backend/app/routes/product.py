from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from io import BytesIO
import openpyxl
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/products", tags=["Products"])


# 🔥 핵심 수정 부분
@router.post("/")
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    code = product.code.strip()
    name = product.name.strip() if product.name else ""

    existing = db.query(models.Product).filter(
        models.Product.new_code == code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 품번")

    db_product = models.Product(
        old_code=(product.old_code or "").strip(),
        new_code=code,
        name=name,
        type=product.type,
        material=(product.material or "").strip(),
        spec=(product.spec or "").strip(),
        quantity=product.quantity or 0,
        location=(product.location or "").strip(),
        min_stock=product.min_stock,
        supplier_company_id=product.supplier_company_id
    )

    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return db_product


@router.post("/import-parts")
def import_parts(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일이 없습니다")

    content = file.file.read()
    wb = openpyxl.load_workbook(BytesIO(content))
    ws = wb.active

    header = [cell.value for cell in ws[1]]
    col = {name: idx for idx, name in enumerate(header)}

    required = ["기존품번", "신품번", "품명", "규격", "재질", "재고수량", "최소재고", "보관위치", "발주처"]
    for r in required:
        if r not in col:
            raise HTTPException(status_code=400, detail=f"엑셀 형식 오류: {r} 컬럼 없음")

    created = 0
    updated = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        old_code = str(row[col["기존품번"]] or "").strip()
        new_code = str(row[col["신품번"]] or "").strip()
        name = str(row[col["품명"]] or "").strip()
        spec = str(row[col["규격"]] or "").strip()
        material = str(row[col["재질"]] or "").strip()
        quantity = int(row[col["재고수량"]] or 0)
        min_stock = int(row[col["최소재고"]] or 0)
        location = (row[col["보관위치"]] or "").strip()
        supplier_name = str(row[col["발주처"]] or "").strip()

        if not new_code:
            continue

        supplier_id = None
        if supplier_name:
            company = db.query(models.Company).filter(
                models.Company.name == supplier_name
            ).first()
            if not company:
                company = models.Company(name=supplier_name, phone="", fax="", address="")
                db.add(company)
                db.commit()
                db.refresh(company)
            supplier_id = company.id

        product = db.query(models.Product).filter(
            models.Product.new_code == new_code
        ).first()

        if product:
            product.old_code = old_code
            product.name = name
            product.type = "PART"
            product.material = material
            product.spec = spec
            product.quantity = quantity
            product.min_stock = min_stock
            product.location = location
            product.supplier_company_id = supplier_id
            updated += 1
        else:
            db.add(models.Product(
                old_code=old_code,
                new_code=new_code,
                name=name,
                type="PART",
                material=material,
                spec=spec,
                quantity=quantity,
                min_stock=min_stock,
                location=location,
                supplier_company_id=supplier_id
            ))
            created += 1

    db.commit()

    return {"created": created, "updated": updated}


@router.post("/import-finished")
def import_finished(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일이 없습니다")

    content = file.file.read()
    wb = openpyxl.load_workbook(BytesIO(content))
    ws = wb.active

    header = [cell.value for cell in ws[1]]
    col = {name: idx for idx, name in enumerate(header)}

    required = ["기존품번", "신품번", "품명", "규격", "재질", "BOM", "발주처"]
    for r in required:
        if r not in col:
            raise HTTPException(status_code=400, detail=f"엑셀 형식 오류: {r} 컬럼 없음")

    created = 0
    updated = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        old_code = str(row[col["기존품번"]] or "").strip()
        new_code = str(row[col["신품번"]] or "").strip()
        name = str(row[col["품명"]] or "").strip()
        spec = str(row[col["규격"]] or "").strip()
        material = str(row[col["재질"]] or "").strip()
        bom_text = (row[col["BOM"]] or "").strip()
        supplier_name = str(row[col["발주처"]] or "").strip()

        if not new_code:
            continue

        supplier_id = None
        if supplier_name:
            company = db.query(models.Company).filter(
                models.Company.name == supplier_name
            ).first()
            if not company:
                company = models.Company(name=supplier_name, phone="", fax="", address="")
                db.add(company)
                db.commit()
                db.refresh(company)
            supplier_id = company.id

        product = db.query(models.Product).filter(
            models.Product.new_code == new_code
        ).first()

        if product:
            product.old_code = old_code
            product.name = name
            product.type = "FINISHED"
            product.material = material
            product.spec = spec
            product.supplier_company_id = supplier_id
            updated += 1
        else:
            db.add(models.Product(
                old_code=old_code,
                new_code=new_code,
                name=name,
                type="FINISHED",
                material=material,
                spec=spec,
                quantity=0,
                min_stock=0,
                location="",
                supplier_company_id=supplier_id
            ))
            created += 1

        if bom_text:
            for chunk in bom_text.split(","):
                part = chunk.strip()
                if not part or ":" not in part:
                    continue
                child_code, qty_text = part.split(":", 1)
                child_code = child_code.strip()
                try:
                    qty = int(qty_text.strip())
                except Exception:
                    continue

                existing = db.query(models.BOM).filter(
                    models.BOM.parent_code == new_code,
                    models.BOM.child_code == child_code
                ).first()
                if not existing:
                    db.add(models.BOM(
                        parent_code=new_code,
                        child_code=child_code,
                        quantity=qty
                    ))

    db.commit()

    return {"created": created, "updated": updated}


@router.get("/")
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()


@router.delete("/{product_code}")
def delete_product(product_code: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(
        models.Product.new_code == product_code
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="제품 없음")

    # 제품 삭제 시 참조되는 기본 데이터 정리
    db.query(models.BOM).filter(
        or_(
            models.BOM.parent_code == product_code,
            models.BOM.child_code == product_code
        )
    ).delete(synchronize_session=False)

    db.delete(product)
    db.commit()

    return {"message": "삭제 완료"}


# ⭐ 제품 수정
@router.put("/{product_code}")
def update_product(product_code: str, data: dict, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(
        models.Product.new_code == product_code
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="제품 없음")

    product.old_code = data.get("old_code", product.old_code)
    product.name = data.get("name", product.name)
    product.type = data.get("type", product.type)
    product.material = data.get("material", product.material)
    product.spec = data.get("spec", product.spec)
    product.location = data.get("location", product.location)
    product.min_stock = data.get("min_stock", product.min_stock)
    product.quantity = data.get("quantity", product.quantity)
    product.supplier_company_id = data.get(
        "supplier_company_id", product.supplier_company_id
    )

    db.commit()
    return product
