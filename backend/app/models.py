from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    email = Column(String)
    phone = Column(String)
    address = Column(String)
    fax = Column(String)

class CompanyEmployee(Base):
    __tablename__ = "company_employees"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    department = Column(String)
    name = Column(String)
    title = Column(String)
    phone = Column(String)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    old_code = Column(String)
    new_code = Column(String, unique=True)
    name = Column(String)
    type = Column(String)
    material = Column(String)
    spec = Column(String)
    quantity = Column(Integer, default=0)
    min_stock = Column(Integer, default=0)
    location = Column(String)
    supplier_company_id = Column(Integer, ForeignKey("companies.id"))


class BOM(Base):
    __tablename__ = "bom"

    id = Column(Integer, primary_key=True)
    parent_code = Column(String)
    child_code = Column(String)
    quantity = Column(Integer)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    product_code = Column(String)
    quantity = Column(Integer)
    company = Column(String)
    status = Column(String, default="WAIT")
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    product_code = Column(String)
    quantity = Column(Integer)
    type = Column(String)
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
