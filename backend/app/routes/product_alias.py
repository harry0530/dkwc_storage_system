from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

router = APIRouter(prefix="/product-alias", tags=["ProductAlias"])


@router.post("/")
def create_alias(data: dict, db: Session = Depends(get_db)):
    alias = models.ProductAlias(
        product_code=data["product_code"],
        company=data["company"],
        alias_code=data["alias_code"]
    )

    db.add(alias)
    db.commit()

    return {"message": "alias 등록 완료"}


@router.get("/")
def get_alias(db: Session = Depends(get_db)):
    return db.query(models.ProductAlias).all()


# ✅ alias 수정
@router.put("/{alias_id}")
def update_alias(alias_id: int, data: dict, db: Session = Depends(get_db)):
    alias = db.query(models.ProductAlias).filter(
        models.ProductAlias.id == alias_id
    ).first()

    if not alias:
        raise HTTPException(status_code=404, detail="alias 없음")

    alias.company = data.get("company", alias.company)
    alias.alias_code = data.get("alias_code", alias.alias_code)
    alias.product_code = data.get("product_code", alias.product_code)

    db.commit()
    return {"message": "수정 완료"}


# ✅ alias 삭제
@router.delete("/{alias_id}")
def delete_alias(alias_id: int, db: Session = Depends(get_db)):
    alias = db.query(models.ProductAlias).filter(
        models.ProductAlias.id == alias_id
    ).first()

    if not alias:
        raise HTTPException(status_code=404, detail="alias 없음")

    db.delete(alias)
    db.commit()

    return {"message": "삭제 완료"}
