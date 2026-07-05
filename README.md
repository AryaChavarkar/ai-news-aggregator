

# AI News Aggregator API

A production-style REST API that fetches real-time news, uses AI to summarize and categorize articles, and supports semantic search using vector embeddings.

## Tech Stack
- **Framework**: FastAPI + SQLAlchemy
- **Database**: PostgreSQL (Supabase cloud) + pgvector
- **AI**: Groq (LLaMA3-70B) for summarization, categorization, sentiment
- **Auth**: JWT Authentication with bcrypt
- **Search**: Semantic search using vector embeddings
- **Background Tasks**: Celery + Redis (in progress)
- **News Source**: NewsAPI.org

## Features
- Fetch real-time news by category
- AI-powered article summarization and sentiment analysis
- JWT user authentication
- Semantic similarity search
- Personalized news feed by category
- Auto-generated Swagger documentation at /docs

## Setup
1. Clone the repo
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/Scripts/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create `.env` file with your API keys
6. Run: `uvicorn app.main:app --reload --port 8080`

## API Routes
| Method | Route | Description |
|--------|-------|-------------|
| GET | /health | Health check |
| POST | /register | Create account |
| POST | /login | Get JWT token |
| GET | /news | Get articles (filter by category) |
| POST | /fetch-news | Fetch from NewsAPI |
| POST | /summarize-all | AI summarize all articles |
| GET | /search/similar/{id} | Find similar articles |
| GET | /profile | Protected user profile |
