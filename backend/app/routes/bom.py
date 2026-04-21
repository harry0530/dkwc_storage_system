from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/bom", tags=["BOM"])


@router.post("/")
def create_bom(bom: schemas.BOMCreate, db: Session = Depends(get_db)):
    return crud.create_bom(db, bom)


@router.get("/{product_code}")
def get_bom(product_code: str, db: Session = Depends(get_db)):
    return crud.get_bom_by_product(db, product_code)


@router.get("/")
def get_all_bom(db: Session = Depends(get_db)):
    return crud.get_all_bom(db)


@router.delete("/{bom_id}")
def delete_bom(bom_id: int, db: Session = Depends(get_db)):
    return crud.delete_bom(db, bom_id)


@router.put("/{bom_id}")
def update_bom(bom_id: int, data: schemas.BOMUpdate, db: Session = Depends(get_db)):
    return crud.update_bom(db, bom_id, data)
