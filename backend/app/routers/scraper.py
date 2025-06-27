from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient
import os
from ..routers.auth import get_current_user, User

router = APIRouter()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.news_db

# News sources configuration
NEWS_SOURCES = [
    {
        "name": "Example Tech News",
        "url": "https://example.com/tech",
        "article_selector": "article",
        "title_selector": "h2",
        "content_selector": ".content",
        "image_selector": "img.featured",
    },
    # Add more sources as needed
]

async def fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch page content with error handling and retries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 404:
                    raise HTTPException(status_code=404, detail=f"Page not found: {url}")
                else:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Error fetching {url}: {response.status}"
                    )
        except Exception as e:
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to fetch {url} after {max_retries} attempts: {str(e)}"
                )
            await asyncio.sleep(1)

async def parse_article(html: str, source_config: dict) -> dict:
    """Parse article content using BeautifulSoup."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract article information based on selectors
    title_elem = soup.select_one(source_config["title_selector"])
    content_elem = soup.select_one(source_config["content_selector"])
    image_elem = soup.select_one(source_config["image_selector"])
    
    if not title_elem or not content_elem:
        return None
        
    # Extract and clean text
    title = title_elem.get_text().strip()
    content = content_elem.get_text().strip()
    image_url = image_elem.get("src") if image_elem else None
    
    # Create summary (first few sentences or paragraphs)
    summary = " ".join(content.split(". ")[:3]) + "..."
    
    return {
        "title": title,
        "content": content,
        "summary": summary,
        "image_url": image_url,
        "source_name": source_config["name"],
        "source_url": source_config["url"],
        "publication_date": datetime.utcnow(),
        "categories": ["technology"],  # You might want to implement category detection
    }

async def scrape_source(session: aiohttp.ClientSession, source_config: dict) -> List[dict]:
    """Scrape articles from a single source."""
    try:
        html = await fetch_page(session, source_config["url"])
        soup = BeautifulSoup(html, 'html.parser')
        
        articles = []
        for article_elem in soup.select(source_config["article_selector"]):
            if article_url := article_elem.get("href"):
                article_html = await fetch_page(session, article_url)
                if article_data := await parse_article(article_html, source_config):
                    articles.append(article_data)
                    
        return articles
    except Exception as e:
        print(f"Error scraping {source_config['name']}: {str(e)}")
        return []

async def run_scraper():
    """Main scraper function that processes all sources."""
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_source(session, source) for source in NEWS_SOURCES]
        results = await asyncio.gather(*tasks)
        
        # Flatten results and filter out None values
        articles = [
            article for source_articles in results 
            for article in source_articles if article
        ]
        
        # Store in database
        if articles:
            await db.news.insert_many(articles)
        
        return {
            "message": f"Successfully scraped {len(articles)} articles",
            "articles_count": len(articles)
        }

@router.post("/run")
async def trigger_scraper(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Trigger the scraper to run in the background.
    Only authenticated users can trigger the scraper.
    """
    background_tasks.add_task(run_scraper)
    return {"message": "Scraper started in background"}

@router.get("/status")
async def get_scraper_status(current_user: User = Depends(get_current_user)):
    """
    Get the status of the last scraping operation.
    """
    last_run = await db.scraper_logs.find_one(
        sort=[("timestamp", -1)]
    )
    
    if not last_run:
        return {
            "last_run": None,
            "status": "Never run",
            "articles_count": 0
        }
        
    return {
        "last_run": last_run["timestamp"],
        "status": last_run["status"],
        "articles_count": last_run["articles_count"]
    }

@router.post("/add-source")
async def add_news_source(
    name: str,
    url: str,
    selectors: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Add a new news source to scrape.
    Only admin users should be able to add new sources.
    """
    # Here you might want to add admin-only check
    new_source = {
        "name": name,
        "url": url,
        **selectors
    }
    
    await db.sources.insert_one(new_source)
    return {"message": "News source added successfully"}
