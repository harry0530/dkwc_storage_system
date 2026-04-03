from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/bom", tags=["BOM"])


# ⭐ BOM 등록
@router.post("/")
def create_bom(bom: schemas.BOMCreate, db: Session = Depends(get_db)):
    return crud.create_bom(db, bom)


# ⭐ 특정 제품 BOM 조회
@router.get("/{product_code}")
def get_bom(product_code: str, db: Session = Depends(get_db)):
    return crud.get_bom_by_product(db, product_code)


# ⭐ 전체 BOM 조회 (추가)
@router.get("/")
def get_all_bom(db: Session = Depends(get_db)):
    return crud.get_all_bom(db)


# ⭐ 삭제 (추가)
@router.delete("/{bom_id}")
def delete_bom(bom_id: int, db: Session = Depends(get_db)):
    return crud.delete_bom(db, bom_id)