import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"

async def fetch_news(category="general", country="us"):
    # This function calls the News API and returns articles
    params = {
        "apiKey": NEWS_API_KEY,
        "category": category,
        "country": country,
        "pageSize": 10  # fetch 10 articles at a time
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(NEWS_API_URL, params=params) as response:
            data = await response.json()
            
            if data["status"] == "ok":
                return data["articles"]
            return []