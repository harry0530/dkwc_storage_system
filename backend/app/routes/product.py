from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from io import BytesIO
import openpyxl
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/products", tags=["Products"])


# ?뵦 ?듭떖 ?섏젙 遺遺?@router.post("/")
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    code = product.code.strip()
    name = product.name.strip() if product.name else ""

    existing = db.query(models.Product).filter(
        models.Product.new_code == code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="?대? 議댁옱?섎뒗 ?덈쾲")

    db_product = models.Product(
        old_code=(product.old_code or "").strip(),
        new_code=code,
        drawing_number=(product.drawing_number or "").strip(),
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
        raise HTTPException(status_code=400, detail="?뚯씪???놁뒿?덈떎")

    content = file.file.read()
    wb = openpyxl.load_workbook(BytesIO(content))

    def normalize(value):
        return str(value or "").strip()

    def normalize_code(value):
        raw = normalize(value)
        if raw.endswith(".0"):
            trimmed = raw[:-2]
            if trimmed.isdigit():
                return trimmed
        return raw

    def build_header_map(values):
        header_values = [normalize(v) for v in values]
        mapping = {name: idx for idx, name in enumerate(header_values) if name}
        if "援ы뭹踰? in mapping and "湲곗〈?덈쾲" not in mapping:
            mapping["湲곗〈?덈쾲"] = mapping["援ы뭹踰?"]
        if "도번" in mapping and "drawing_number" not in mapping:
            mapping["drawing_number"] = mapping["도번"]
        return header_values, mapping

    ws = wb.active
    header_row = 1
    header, col = build_header_map([cell.value for cell in ws[1]])

    if not col:
        for name in wb.sheetnames:
            candidate = wb[name]
            if candidate.max_row < 2:
                continue
            candidate_header, candidate_col = build_header_map(
                [cell.value for cell in candidate[1]]
            )
            if candidate_col:
                ws = candidate
                header = candidate_header
                col = candidate_col
                header_row = 1
                break

    if "?좏뭹踰? not in col:
        for row_idx in range(1, min(ws.max_row, 10) + 1):
            candidate_header, candidate_col = build_header_map(
                [cell.value for cell in ws[row_idx]]
            )
            if "?좏뭹踰? in candidate_col:
                header = candidate_header
                col = candidate_col
                header_row = row_idx
                break

    if ws.max_row <= header_row:
        best = None
        for name in wb.sheetnames:
            candidate = wb[name]
            if candidate.max_row <= 1:
                continue
            for row_idx in range(1, min(candidate.max_row, 10) + 1):
                candidate_header, candidate_col = build_header_map(
                    [cell.value for cell in candidate[row_idx]]
                )
                if "?좏뭹踰? in candidate_col:
                    score = candidate.max_row
                    if best is None or score > best[0]:
                        best = (score, candidate, candidate_header, candidate_col, row_idx)
                    break
        if best:
            _, ws, header, col, header_row = best

    required = ["湲곗〈?덈쾲", "?좏뭹踰?", "?덈챸", "洹쒓꺽", "?ъ쭏", "?ш퀬?섎웾", "理쒖냼?ш퀬", "蹂닿??꾩튂", "諛쒖＜泥?"]
    for r in required:
        if r not in col:
            raise HTTPException(status_code=400, detail=f"?묒? ?뺤떇 ?ㅻ쪟: {r} 而щ읆 ?놁쓬")

    created = 0
    updated = 0
    skipped = 0
    rows_total = 0

    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if row and any(value not in (None, "") for value in row):
            rows_total += 1
        old_code = normalize_code(row[col["湲곗〈?덈쾲"]])
        new_code = normalize_code(row[col["?좏뭹踰?"]])
        drawing_number = normalize(row[col["drawing_number"]]) if "drawing_number" in col else ""
        name = normalize(row[col["?덈챸"]])
        spec = normalize(row[col["洹쒓꺽"]])
        material = normalize(row[col["?ъ쭏"]])
        quantity = int(row[col["?ш퀬?섎웾"]] or 0)
        min_stock = int(row[col["理쒖냼?ш퀬"]] or 0)
        location = normalize(row[col["蹂닿??꾩튂"]])
        supplier_name = normalize(row[col["諛쒖＜泥?"]])

        if not new_code:
            skipped += 1
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
            product.drawing_number = drawing_number
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
                drawing_number=drawing_number,
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

    sample_rows = []
    for row in ws.iter_rows(min_row=1, max_row=min(3, ws.max_row), values_only=True):
        sample_rows.append([normalize(value) for value in row])

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "rows_total": rows_total,
        "sheet": ws.title,
        "header": header,
        "max_row": ws.max_row,
        "max_column": ws.max_column,
        "header_row": header_row,
        "sample_rows": sample_rows
    }


@router.post("/import-finished")
def import_finished(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="?뚯씪???놁뒿?덈떎")

    content = file.file.read()
    wb = openpyxl.load_workbook(BytesIO(content))
    ws = wb.active

    header = [cell.value for cell in ws[1]]
    col = {name: idx for idx, name in enumerate(header)}

    required = ["湲곗〈?덈쾲", "?좏뭹踰?", "?덈챸", "洹쒓꺽", "?ъ쭏", "BOM", "諛쒖＜泥?"]
    for r in required:
        if r not in col:
            raise HTTPException(status_code=400, detail=f"?묒? ?뺤떇 ?ㅻ쪟: {r} 而щ읆 ?놁쓬")

    created = 0
    updated = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        old_code = str(row[col["湲곗〈?덈쾲"]] or "").strip()
        new_code = str(row[col["?좏뭹踰?"]] or "").strip()
        drawing_number = str(row[col["도번"]] or "").strip() if "도번" in col else ""
        name = str(row[col["?덈챸"]] or "").strip()
        spec = str(row[col["洹쒓꺽"]] or "").strip()
        material = str(row[col["?ъ쭏"]] or "").strip()
        bom_text = (row[col["BOM"]] or "").strip()
        supplier_name = str(row[col["諛쒖＜泥?"]] or "").strip()

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
            product.drawing_number = drawing_number
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
                drawing_number=drawing_number,
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
        raise HTTPException(status_code=404, detail="?쒗뭹 ?놁쓬")

    # ?쒗뭹 ??젣 ??李몄“?섎뒗 湲곕낯 ?곗씠???뺣━
    db.query(models.BOM).filter(
        or_(
            models.BOM.parent_code == product_code,
            models.BOM.child_code == product_code
        )
    ).delete(synchronize_session=False)

    db.delete(product)
    db.commit()

    return {"message": "??젣 ?꾨즺"}


# 狩??쒗뭹 ?섏젙
@router.put("/{product_code}")
def update_product(product_code: str, data: dict, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(
        models.Product.new_code == product_code
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="?쒗뭹 ?놁쓬")

    product.old_code = data.get("old_code", product.old_code)
    product.drawing_number = data.get("drawing_number", product.drawing_number)
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
