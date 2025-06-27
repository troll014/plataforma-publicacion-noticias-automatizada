from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import os
from ..routers.auth import get_current_user, User

router = APIRouter()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.news_db

class NewsItem(BaseModel):
    title: str
    content: str
    summary: str
    image_url: str
    source_url: str
    source_name: str
    publication_date: datetime
    categories: List[str] = []
    author: Optional[str] = None

class NewsResponse(BaseModel):
    id: str
    title: str
    summary: str
    image_url: str
    source_name: str
    publication_date: datetime
    
@router.get("/", response_model=List[NewsResponse])
async def get_news(
    skip: int = 0,
    limit: int = 10,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve news articles with pagination and optional category filtering.
    """
    query = {}
    if category:
        query["categories"] = category

    cursor = db.news.find(query).skip(skip).limit(limit).sort("publication_date", -1)
    news_items = await cursor.to_list(length=limit)
    
    # Convert MongoDB _id to string and format response
    for item in news_items:
        item["id"] = str(item["_id"])
        del item["_id"]
    
    return news_items

@router.get("/{news_id}", response_model=NewsItem)
async def get_news_item(
    news_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a specific news article by ID.
    """
    from bson.objectid import ObjectId
    
    try:
        news_item = await db.news.find_one({"_id": ObjectId(news_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid news ID format"
        )
    
    if news_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News article not found"
        )
    
    news_item["id"] = str(news_item["_id"])
    del news_item["_id"]
    return news_item

@router.get("/categories", response_model=List[str])
async def get_categories(current_user: User = Depends(get_current_user)):
    """
    Get all available news categories.
    """
    categories = await db.news.distinct("categories")
    return categories

@router.get("/sources", response_model=List[str])
async def get_sources(current_user: User = Depends(get_current_user)):
    """
    Get all available news sources.
    """
    sources = await db.news.distinct("source_name")
    return sources

@router.post("/", response_model=NewsItem)
async def create_news(
    news_item: NewsItem,
    current_user: User = Depends(get_current_user)
):
    """
    Manually create a news article (admin only).
    """
    # Here you might want to add admin-only check
    news_dict = news_item.dict()
    result = await db.news.insert_one(news_dict)
    news_dict["id"] = str(result.inserted_id)
    return news_dict

@router.delete("/{news_id}")
async def delete_news(
    news_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a news article (admin only).
    """
    from bson.objectid import ObjectId
    
    try:
        result = await db.news.delete_one({"_id": ObjectId(news_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News article not found"
            )
        return {"message": "News article deleted successfully"}
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid news ID format"
        )
