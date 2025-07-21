from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv
import os
from models.product.model import ProductCreateModel
from models.order.model import OrderCreateModel


app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB configuration
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["ecommerce"]
products_collection = db["products"]
orders_collection = db["orders"]

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
        results.append({
            "id": str(doc["_id"]),
            "name": doc["name"],
            "price": doc["price"]
        })
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
            product = await products_collection.find_one({"_id": obj_id})
            if not product:
                raise HTTPException(status_code=404, detail=f"Product not found: {item['productId']}")
            new_items.append({
                "productId": obj_id,
                "qty": item["qty"]
            })
        except Exception:
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
        for item in doc.get("items", []):
            try:
                product = await products_collection.find_one({"_id": item["productId"]})
                product_name = product["name"] if product else "Unknown"
            except:
                product_name = "Unknown"

            order_items.append({
                "productId": str(item["productId"]),
                "productName": product_name,
                "qty": item["qty"]
            })

        orders.append({
            "id": str(doc["_id"]),
            "items": order_items
        })

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
    uvicorn.run("server:app", host="0.0.0.0", port=10000)
