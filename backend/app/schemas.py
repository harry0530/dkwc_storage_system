from pydantic import BaseModel
from typing import Optional


class ProductCreate(BaseModel):
    code: str  # new_code
    name: str
    type: str
    location: Optional[str] = ""
    min_stock: int
    old_code: Optional[str] = ""
    drawing_number: Optional[str] = ""
    material: Optional[str] = ""
    spec: Optional[str] = ""
    heat_treatment: Optional[str] = ""
    welding: Optional[str] = ""
    plating: Optional[str] = ""
    supplier_company_id: Optional[int] = None
    quantity: Optional[int] = 0


class BOMCreate(BaseModel):
    parent_code: str
    child_code: str
    quantity: int


class BOMUpdate(BaseModel):
    child_code: str
    quantity: int


class InventoryCreate(BaseModel):
    product_code: str
    quantity: int
    reason: Optional[str] = None


class OrderCreate(BaseModel):
    product_code: str
    quantity: int
    company: str


class PurchaseOrderCreate(BaseModel):
    product_code: str
    quantity: int
    company: str


class PurchaseReceive(BaseModel):
    quantity: int


class PurchaseOrderItemCreate(BaseModel):
    product_code: str
    quantity: int


class PurchaseOrderBatchCreate(BaseModel):
    company: Optional[str] = None
    items: list[PurchaseOrderItemCreate]
    due_date: Optional[str] = None  # YYYY-MM-DD


class PurchaseOrderReceiptOut(BaseModel):
    id: int
    purchase_order_id: int
    quantity: int
    created_at: str


class PurchaseOrderUpdate(BaseModel):
    product_code: Optional[str] = None
    quantity: Optional[int] = None
    company: Optional[str] = None


class PurchaseReceiptUpdate(BaseModel):
    quantity: Optional[int] = None
    created_at: Optional[str] = None
