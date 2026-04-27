from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, crud
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from urllib.parse import quote
import os
import re

router = APIRouter(prefix="/inventory", tags=["Inventory"])


FACTORY_LAYOUT_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "templates",
    "factory_layout_template.xlsx",
)


def _normalize_location_code(value: str) -> str:
    raw = (value or "").strip().upper()
    if not raw:
        return ""
    match = re.match(r"^([A-Z])\s*-\s*([0-9]{1,3})$", raw)
    if match:
        zone = match.group(1)
        num = match.group(2)
        if len(num) == 1:
            num = f"0{num}"
        return f"{zone}-{num}"
    return re.sub(r"\s+", "", raw)


def _find_location_cell(workbook, location_code: str):
    target = _normalize_location_code(location_code)
    for ws in workbook.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if _normalize_location_code(str(cell.value or "")) == target:
                    return ws, cell
    return None, None


def _fill_location_cell(ws, cell, fill):
    # Usually location codes are single cells, but this keeps merged cells safe too.
    for merged_range in ws.merged_cells.ranges:
        if cell.coordinate in merged_range:
            for row in ws[merged_range.coord]:
                for merged_cell in row:
                    merged_cell.fill = fill
            return
    cell.fill = fill


# ✅ 재고 조회 (JOIN 버전)
@router.get("/")
def get_inventory(db: Session = Depends(get_db)):
    result = []

    inventory_list = db.query(models.Product).filter(
        models.Product.type == "PART"
    ).all()

    for inv in inventory_list:
        result.append({
            "code": inv.new_code,
            "product_code": inv.new_code,
            "old_code": inv.old_code,
            "new_code": inv.new_code,
            "drawing_number": inv.drawing_number or "",
            "name": inv.name or "",
            "material": inv.material or "",
            "spec": inv.spec or "",
            "heat_treatment": inv.heat_treatment or "",
            "welding": inv.welding or "",
            "plating": inv.plating or "",
            "type": inv.type,
            "location": inv.location or "",
            "quantity": inv.quantity,
            "min_stock": inv.min_stock,
            "supplier_company_id": inv.supplier_company_id
        })

    return result


@router.get("/location-map/{location_code}")
def download_location_map(location_code: str, danger: bool = False):
    normalized_code = _normalize_location_code(location_code)
    if not normalized_code:
        raise HTTPException(status_code=400, detail="보관위치를 입력하세요.")
    if not os.path.exists(FACTORY_LAYOUT_TEMPLATE):
        raise HTTPException(status_code=500, detail="공장 배치도 템플릿을 찾을 수 없습니다.")

    workbook = load_workbook(FACTORY_LAYOUT_TEMPLATE)
    ws, cell = _find_location_cell(workbook, normalized_code)
    if not cell:
        raise HTTPException(status_code=404, detail=f"배치도에서 {normalized_code} 위치를 찾을 수 없습니다.")

    fill_color = "F4CCCC" if danger else "FFF2CC"
    _fill_location_cell(ws, cell, PatternFill(fill_type="solid", fgColor=fill_color))
    workbook.active = workbook.worksheets.index(ws)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    filename = f"factory_layout_{normalized_code}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
    }
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


# ✅ 재고 입력 (복구됨 ⭐)
@router.post("/")
def create_inventory(inv: schemas.InventoryCreate, db: Session = Depends(get_db)):
    return crud.create_inventory(db, inv)


# ✅ 재고 수정 (수량 직접 수정)
@router.put("/{product_code}")
def update_inventory(product_code: str, data: dict, db: Session = Depends(get_db)):
    inv = db.query(models.Product).filter(
        models.Product.new_code == product_code
    ).first()

    if not inv:
        raise HTTPException(status_code=404, detail="재고 없음")

    if "quantity" in data:
        new_qty = data["quantity"]
        prev_qty = inv.quantity
        inv.quantity = new_qty

        diff = new_qty - prev_qty
        if diff != 0:
            reason = data.get("reason") or "수량 변경"
            tx_type = "IN" if diff > 0 else "OUT"
            db.add(models.Transaction(
                product_code=inv.new_code,
                quantity=abs(diff),
                type=tx_type,
                reason=reason
            ))

    db.commit()

    return {"message": "수정 완료"}


# ✅ 재고 삭제 (목록에서 제거)
@router.delete("/{product_code}")
def delete_inventory(product_code: str, db: Session = Depends(get_db)):
    inv = db.query(models.Product).filter(
        models.Product.new_code == product_code
    ).first()

    if not inv:
        raise HTTPException(status_code=404, detail="재고 없음")

    db.delete(inv)
    db.commit()

    return {"message": "삭제 완료"}
