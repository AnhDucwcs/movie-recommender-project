from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Interaction(Base):
    __tablename__ = "interactions"

    interaction_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    movie_id = Column(Integer, index=True, nullable=False)
    interaction_type = Column(String, nullable=False)
    rating_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
