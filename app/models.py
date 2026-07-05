from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base
from pgvector.sqlalchemy import Vector


# s SQLAlchemy code
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    content = Column(Text)
    url = Column(String, unique=True)
    source = Column(String)
    category = Column(String, default="general")
    ai_category = Column(String)
    sentiment = Column(String)
    summary = Column(Text)
    embedding = Column(Vector(1536))
    published_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True)
    preferred_categories = Column(String, default="general")
    email_notifications = Column(Boolean, default=False)
    email = Column(String, nullable=False)
    digest_frequency = Column(String, default="daily")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())