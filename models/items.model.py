from pydantic import BaseModel, Field
from typing import List

class OrderItemModel(BaseModel):
    productId: str = Field(..., example="60f5b2c9c6e4a1c8e4a4b1a1")
    qty: int = Field(..., example=3)

class OrderCreateModel(BaseModel):
    userId: str = Field(..., example="user_1")
    items: List[OrderItemModel]
