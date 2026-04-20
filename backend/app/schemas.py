from pydantic import BaseModel


class ProductCreate(BaseModel):
    code: str  # new_code
    name: str
    type: str
    location: str | None = ""
    min_stock: int
    old_code: str | None = ""
    drawing_number: str | None = ""
    material: str | None = ""
    spec: str | None = ""
    supplier_company_id: int | None = None
    quantity: int | None = 0


class BOMCreate(BaseModel):
    parent_code: str
    child_code: str
    quantity: int


class InventoryCreate(BaseModel):
    product_code: str
    quantity: int
    reason: str | None = None


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
    company: str
    items: list[PurchaseOrderItemCreate]


class PurchaseOrderReceiptOut(BaseModel):
    id: int
    purchase_order_id: int
    quantity: int
    created_at: str


class PurchaseOrderUpdate(BaseModel):
    product_code: str | None = None
    quantity: int | None = None
    company: str | None = None


class PurchaseReceiptUpdate(BaseModel):
    quantity: int | None = None
    created_at: str | None = None
