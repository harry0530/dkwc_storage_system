from pydantic import BaseModel


class ProductCreate(BaseModel):
    code: str  # new_code
    name: str
    type: str
    location: str | None = ""
    min_stock: int
    old_code: str | None = ""
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
