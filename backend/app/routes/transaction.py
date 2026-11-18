from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, models

router = APIRouter(prefix="/transactions", tags=["Transaction"])


@router.get("/")
def get_transactions(db: Session = Depends(get_db)):
    return crud.get_transactions(db)


@router.get("/history")
def get_transaction_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=10, le=100),
    search: str = Query("", max_length=120),
    transaction_type: str = Query("", alias="type", max_length=3),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    reconstructed_only: bool = False,
    db: Session = Depends(get_db),
):
    """Searchable, paginated inventory history for the operations UI."""

    query = (
        db.query(
            models.Transaction,
            models.Product.name.label("product_name"),
            models.HistoricalImport.company.label("company"),
            models.HistoricalImport.source_file.label("source_file"),
            models.HistoricalImport.source_sheet.label("source_sheet"),
        )
        .outerjoin(
            models.Product,
            models.Product.new_code == models.Transaction.product_code,
        )
        .outerjoin(
            models.HistoricalImport,
            models.HistoricalImport.transaction_id == models.Transaction.id,
        )
    )

    normalized_search = search.strip()
    if normalized_search:
        term = f"%{normalized_search}%"
        query = query.filter(
            or_(
                models.Transaction.product_code.ilike(term),
                models.Product.name.ilike(term),
                models.HistoricalImport.company.ilike(term),
                models.HistoricalImport.source_file.ilike(term),
            )
        )

    normalized_type = transaction_type.strip().upper()
    if normalized_type in {"IN", "OUT"}:
        query = query.filter(models.Transaction.type == normalized_type)
    if start_date:
        query = query.filter(
            models.Transaction.created_at >= datetime.combine(start_date, time.min)
        )
    if end_date:
        query = query.filter(
            models.Transaction.created_at < datetime.combine(end_date + timedelta(days=1), time.min)
        )
    if reconstructed_only:
        query = query.filter(models.HistoricalImport.id.isnot(None))

    summary = query.with_entities(
        func.count(models.Transaction.id),
        func.coalesce(
            func.sum(case((models.Transaction.type == "IN", 1), else_=0)), 0
        ),
        func.coalesce(
            func.sum(case((models.Transaction.type == "OUT", 1), else_=0)), 0
        ),
        func.coalesce(
            func.sum(
                case(
                    (models.Transaction.type == "IN", models.Transaction.quantity),
                    else_=0,
                )
            ),
            0,
        ),
        func.coalesce(
            func.sum(
                case(
                    (models.Transaction.type == "OUT", models.Transaction.quantity),
                    else_=0,
                )
            ),
            0,
        ),
    ).one()

    rows = (
        query.order_by(models.Transaction.created_at.desc(), models.Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for transaction, product_name, company, source_file, source_sheet in rows:
        items.append(
            {
                "id": transaction.id,
                "created_at": transaction.created_at,
                "product_code": transaction.product_code,
                "product_name": product_name,
                "quantity": transaction.quantity,
                "type": transaction.type,
                "reason": transaction.reason,
                "company": company,
                "source_file": source_file,
                "source_sheet": source_sheet,
                "is_reconstructed": source_file is not None,
            }
        )

    total = int(summary[0] or 0)
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "summary": {
            "total": total,
            "in_count": int(summary[1] or 0),
            "out_count": int(summary[2] or 0),
            "in_quantity": int(summary[3] or 0),
            "out_quantity": int(summary[4] or 0),
        },
    }
