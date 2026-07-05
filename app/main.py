from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import engine, get_db
from app import models
from app.news_fetcher import fetch_news
from app.auth import hash_password, verify_password, create_access_token, verify_token
from app.summarizer import analyze_article
from pydantic import BaseModel
from datetime import datetime

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI News Aggregator", version="1.0")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class PreferenceUpdate(BaseModel):
    preferred_categories: str  # e.g. "technology,sports,business"
    email_notifications: bool
    digest_frequency: str  # "daily" or "weekly"

    
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.username == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.get("/health")
def health_check():
    return {"status": "running", "message": "AI News Aggregator is live!"}

@app.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    return {"message": f"User {user.username} registered successfully!"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/news")
def get_news(category: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Article)
    if category:
        query = query.filter(models.Article.ai_category == category)
    articles = query.all()
    return {"total": len(articles), "articles": articles}

@app.post("/fetch-news")
async def fetch_and_store_news(category: str = "general", db: Session = Depends(get_db)):
    articles = await fetch_news(category=category)
    saved = 0
    for article in articles:
        exists = db.query(models.Article).filter(models.Article.url == article["url"]).first()
        if not exists:
            new_article = models.Article(
                title=article.get("title"),
                description=article.get("description"),
                content=article.get("content"),
                url=article.get("url"),
                source=article.get("source", {}).get("name"),
                published_at=datetime.now()
            )
            db.add(new_article)
            saved += 1
    db.commit()
    return {"message": f"Fetched and saved {saved} new articles", "category": category}

@app.post("/summarize/{article_id}")
def summarize_article(article_id: int, db: Session = Depends(get_db)):
    # Find article by ID
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Call Groq AI to analyze it
    result = analyze_article(article.title, article.description)

    # Save results back to database
    article.summary = result.get("summary")
    article.sentiment = result.get("sentiment")
    article.ai_category = result.get("category")
    db.commit()

    return {
        "article_id": article_id,
        "title": article.title,
        "summary": article.summary,
        "sentiment": article.sentiment,
        "ai_category": article.ai_category
    }


@app.post("/summarize-all")
def summarize_all(db: Session = Depends(get_db)):
    # Get all articles that haven't been summarized yet
    articles = db.query(models.Article).filter(models.Article.summary == None).all()
    count = 0
    for article in articles:
        try:
            result = analyze_article(article.title, article.description)
            article.summary = result.get("summary")
            article.sentiment = result.get("sentiment")
            article.ai_category = result.get("category")
            count += 1
        except Exception as e:
            continue
    db.commit()
    return {"message": f"Summarized {count} articles successfully!"}

@app.post("/generate-embeddings")
def generate_embeddings(db: Session = Depends(get_db)):
    from app.summarizer import get_embedding
    articles = db.query(models.Article).filter(models.Article.embedding == None).all()
    count = 0
    for article in articles:
        try:
            text = f"{article.title} {article.description}"
            embedding = get_embedding(text)
            article.embedding = embedding
            db.commit()  # commit after EACH article
            count += 1
        except Exception as e:
            db.rollback()
            continue
    return {"message": f"Generated embeddings for {count} articles!"}

@app.get("/search/similar/{article_id}")
def find_similar(article_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import text
    article = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.embedding is None:
        raise HTTPException(status_code=400, detail="Article has no embedding yet")
    
    # Convert embedding to proper comma separated string
    embedding_list = article.embedding.tolist()
    embedding_str = "[" + ",".join(str(x) for x in embedding_list) + "]"
    
    results = db.execute(text("""
        SELECT id, title, description, ai_category, sentiment,
               1 - (embedding <=> CAST(:embedding AS vector)) as similarity
        FROM articles
        WHERE id != :article_id AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT 5
    """), {
        "embedding": embedding_str,
        "article_id": article_id
    })
    
    similar = []
    for row in results:
        similar.append({
            "id": row.id,
            "title": row.title,
            "description": row.description,
            "ai_category": row.ai_category,
            "sentiment": row.sentiment,
            "similarity_score": round(float(row.similarity), 3)
        })
    
    return {"article": article.title, "similar_articles": similar}

@app.post("/trigger-fetch")
def trigger_background_fetch(category: str = "general"):
    from app.tasks import fetch_and_summarize
    task = fetch_and_summarize.delay(category)
    return {
        "message": "Background fetch started!",
        "task_id": task.id,
        "category": category
    }
@app.get("/profile")
def get_profile(current_user: models.User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "created_at": current_user.created_at
    }

@app.post("/preferences")
def save_preferences(pref: PreferenceUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(models.UserPreference).filter(models.UserPreference.user_id == current_user.id).first()
    if existing:
        existing.preferred_categories = pref.preferred_categories
        existing.email_notifications = pref.email_notifications
        existing.digest_frequency = pref.digest_frequency
    else:
        new_pref = models.UserPreference(
            user_id=current_user.id,
            email=current_user.email,
            preferred_categories=pref.preferred_categories,
            email_notifications=pref.email_notifications,
            digest_frequency=pref.digest_frequency
        )
        db.add(new_pref)
    db.commit()
    return {"message": "Preferences saved successfully!"}

@app.get("/preferences")
def get_preferences(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    pref = db.query(models.UserPreference).filter(models.UserPreference.user_id == current_user.id).first()
    if not pref:
        raise HTTPException(status_code=404, detail="No preferences found, please set them first")
    return {
        "preferred_categories": pref.preferred_categories,
        "email_notifications": pref.email_notifications,
        "digest_frequency": pref.digest_frequency
    }