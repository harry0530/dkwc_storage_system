from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

router = APIRouter(prefix="/companies", tags=["Companies"])


# ⭐ 거래처 등록
@router.post("/")
def create_company(data: dict, db: Session = Depends(get_db)):
    # 중복 체크
    existing = db.query(models.Company).filter(
        models.Company.name == data["name"]
    ).first()

    if existing:
        raise Exception("이미 존재하는 거래처")

    company = models.Company(
        name=data["name"],
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        fax=data.get("fax", ""),
        address=data.get("address", "")
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    return company


# ⭐ 거래처 전체 조회
@router.get("/")
def get_companies(db: Session = Depends(get_db)):
    return db.query(models.Company).all()


# ⭐ 거래처 삭제
@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(
        models.Company.id == company_id
    ).first()

    if not company:
        raise Exception("거래처 없음")

    db.delete(company)
    db.commit()

    return {"message": "삭제 완료"}


# ⭐ 거래처 수정
@router.put("/{company_id}")
def update_company(company_id: int, data: dict, db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(
        models.Company.id == company_id
    ).first()

    if not company:
        raise Exception("거래처 없음")

    company.name = data.get("name", company.name)
    company.email = data.get("email", company.email)
    company.phone = data.get("phone", company.phone)
    company.fax = data.get("fax", company.fax)
    company.address = data.get("address", company.address)

    db.commit()

    return company


# ⭐ 거래처 직원 등록
@router.post("/{company_id}/employees")
def create_employee(company_id: int, data: dict, db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(
        models.Company.id == company_id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="거래처 없음")

    employee = models.CompanyEmployee(
        company_id=company_id,
        department=data.get("department", ""),
        name=data.get("name", ""),
        title=data.get("title", ""),
        phone=data.get("phone", "")
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return employee


# ⭐ 거래처 직원 조회
@router.get("/{company_id}/employees")
def get_employees(company_id: int, db: Session = Depends(get_db)):
    return db.query(models.CompanyEmployee).filter(
        models.CompanyEmployee.company_id == company_id
    ).all()


# ⭐ 거래처 직원 삭제
@router.delete("/employees/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(models.CompanyEmployee).filter(
        models.CompanyEmployee.id == employee_id
    ).first()

    if not employee:
        raise HTTPException(status_code=404, detail="직원 없음")

    db.delete(employee)
    db.commit()

    return {"message": "삭제 완료"}
