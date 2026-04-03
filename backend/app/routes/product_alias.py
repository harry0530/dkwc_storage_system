from fastapi import APIRouter, Depends
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