from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProductBase(BaseModel):
    name: ShortText = Field(max_length=100, examples=["Pão de Queijo"])
    category: ShortText = Field(max_length=50, examples=["Salgados"])
    price: float = Field(gt=0, examples=[6.5])
    size: ShortText = Field(max_length=30, examples=["Unidade"])
    is_available: bool = Field(examples=[True])
    calories: int = Field(ge=0, examples=[180])


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: ShortText | None = Field(default=None, max_length=100)
    category: ShortText | None = Field(default=None, max_length=50)
    price: float | None = Field(default=None, gt=0)
    size: ShortText | None = Field(default=None, max_length=30)
    is_available: bool | None = None
    calories: int | None = Field(default=None, ge=0)


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class OrderBase(BaseModel):
    customer_name: ShortText = Field(max_length=100, examples=["Ana Souza"])
    table_number: int = Field(gt=0, examples=[4])
    payment_method: ShortText = Field(max_length=30, examples=["Pix"])
    total_amount: float = Field(ge=0, examples=[12.5])
    is_takeaway: bool = Field(examples=[False])
    product_id: int = Field(gt=0, examples=[1])


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    customer_name: ShortText | None = Field(default=None, max_length=100)
    table_number: int | None = Field(default=None, gt=0)
    payment_method: ShortText | None = Field(default=None, max_length=30)
    total_amount: float | None = Field(default=None, ge=0)
    is_takeaway: bool | None = None
    product_id: int | None = Field(default=None, gt=0)


class OrderResponse(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class MessageResponse(BaseModel):
    detail: str
