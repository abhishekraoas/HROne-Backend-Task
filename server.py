from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os

app = FastAPI()

# CORS Middleware (if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB config
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/HROne")
client = AsyncIOMotorClient(MONGO_URI)
db = client["ecommerce"]
products_collection = db["products"]
orders_collection = db["orders"]

# Utilities
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

# Models
class SizeModel(BaseModel):
    size: str
    quantity: int

class ProductCreateModel(BaseModel):
    name: str
    price: float
    sizes: List[SizeModel]

class ProductListModel(BaseModel):
    id: str
    name: str
    price: float

class OrderItemModel(BaseModel):
    productId: str
    qty: int

class OrderCreateModel(BaseModel):
    userId: str
    items: List[OrderItemModel]

class OrderItemDetailModel(BaseModel):
    productId: str
    productName: str
    qty: int

class OrderResponseModel(BaseModel):
    id: str
    items: List[OrderItemDetailModel]

# Routes
@app.post("/products", status_code=201)
async def create_product(product: ProductCreateModel):
    result = await products_collection.insert_one(product.dict())
    return {"id": str(result.inserted_id)}

@app.get("/products")
async def list_products(
    name: Optional[str] = None,
    size: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
):
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if size:
        query["sizes.size"] = size
    cursor = products_collection.find(query).skip(offset).limit(limit)
    results = []
    async for doc in cursor:
        results.append({"id": str(doc["_id"]), "name": doc["name"], "price": doc["price"]})
    return {
        "data": results,
        "page": {
            "next": offset + limit,
            "limit": limit,
            "previous": max(offset - limit, 0)
        }
    }

@app.post("/orders", status_code=201)
async def create_order(order: OrderCreateModel):
    order_dict = order.dict()
    new_items = []

    for item in order_dict["items"]:
        try:
            obj_id = ObjectId(item["productId"])
            # Check if product exists before inserting
            product = await products_collection.find_one({"_id": obj_id})
            if not product:
                raise HTTPException(status_code=404, detail=f"Product not found: {item['productId']}")
            new_items.append({"productId": obj_id, "qty": item["qty"]})
        except:
            raise HTTPException(status_code=400, detail="Invalid productId format")

    order_to_save = {
        "userId": order_dict["userId"],
        "items": new_items
    }

    result = await orders_collection.insert_one(order_to_save)
    return {"id": str(result.inserted_id)}



@app.get("/orders/{user_id}")
async def get_orders(user_id: str, limit: int = 10, offset: int = 0):
    query = {"userId": user_id}
    cursor = orders_collection.find(query).skip(offset).limit(limit)
    orders = []
    async for doc in cursor:
        order_items = []
        for item in doc["items"]:
            product = await products_collection.find_one({"_id": ObjectId(item["productId"])})
            order_items.append({
                "productId": item["productId"],
                "productName": product["name"] if product else "Unknown",
                "qty": item["qty"]
            })
        orders.append({"id": str(doc["_id"]), "items": order_items})
    return {
        "data": orders,
        "page": {
            "next": offset + limit,
            "limit": limit,
            "previous": max(offset - limit, 0)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
