from celery import Celery
from app.database import SessionLocal
from app import models
from app.news_fetcher import fetch_news
from app.summarizer import analyze_article
import asyncio

# This creates the Celery app and connects it to Redis
celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery_app.task
def fetch_and_summarize(category="general"):
    # Open a database session
    db = SessionLocal()
    try:
        # Fetch news (run async function in sync context)
        articles = asyncio.run(fetch_news(category=category))
        saved = 0

        for article in articles:
            # Check for duplicates
            exists = db.query(models.Article).filter(
                models.Article.url == article["url"]
            ).first()

            if not exists:
                new_article = models.Article(
                    title=article.get("title"),
                    description=article.get("description"),
                    content=article.get("content"),
                    url=article.get("url"),
                    source=article.get("source", {}).get("name"),
                )
                db.add(new_article)
                db.commit()
                db.refresh(new_article)

                # AI summarize immediately after saving
                try:
                    result = analyze_article(new_article.title, new_article.description)
                    new_article.summary = result.get("summary")
                    new_article.sentiment = result.get("sentiment")
                    new_article.ai_category = result.get("category")
                    db.commit()
                    saved += 1
                except Exception:
                    continue

        return {"saved": saved, "category": category}
    finally:
        db.close()


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Run fetch_and_summarize every 1 hour automatically
    sender.add_periodic_task(3600.0, fetch_and_summarize.s("general"), name="fetch news every hour")
    sender.add_periodic_task(3600.0, fetch_and_summarize.s("technology"), name="fetch tech every hour")
    sender.add_periodic_task(3600.0, fetch_and_summarize.s("sports"), name="fetch sports every hour")
    sender.add_periodic_task(3600.0, fetch_and_summarize.s("business"))
    
    sender.add_periodic_task(3600.0, fetch_and_summarize.s("health"))