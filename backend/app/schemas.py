from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProductCreate(BaseModel):
    code: str
    name: str
    type: str
    location: str
    min_stock: int   # 🔥 추가


class BOMCreate(BaseModel):
    parent_code: str
    child_code: str
    quantity: int


class InventoryCreate(BaseModel):
    product_code: str
    quantity: int


class OrderCreate(BaseModel):
    product_code: str
    quantity: int
    company: str
