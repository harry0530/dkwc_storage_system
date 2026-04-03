from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud

router = APIRouter(prefix="/transactions", tags=["Transaction"])


@router.get("/")
def get_transactions(db: Session = Depends(get_db)):
    return crud.get_transactions(db)