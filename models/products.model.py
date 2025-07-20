from pydantic import BaseModel, Field
from typing import List


class SizeModel(BaseModel):
    size: str = Field(..., example="L")
    quantity: int = Field(..., example=10)


class ProductCreateModel(BaseModel):
    name: str = Field(..., example="Sample")
    price: float = Field(..., example=100.0)
    sizes: List[SizeModel]
