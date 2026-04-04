from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    phone = Column(String)
    address = Column(String)
    fax = Column(String)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    name = Column(String)
    type = Column(String)
    location = Column(String)
    min_stock = Column(Integer, default=0)


class ProductAlias(Base):
    __tablename__ = "product_alias"

    id = Column(Integer, primary_key=True)
    product_code = Column(String, ForeignKey("products.code"))
    company = Column(String)  # ⭐ 지금은 문자열 유지 (간단 버전)
    alias_code = Column(String)


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    product_code = Column(String, unique=True)
    quantity = Column(Integer, default=0)


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
