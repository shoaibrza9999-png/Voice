from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    whatsapp_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    timezone = Column(String, default="UTC")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="owner", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False) # 'income' or 'expense'

    # Relationships
    transactions = relationship("Transaction", back_populates="category")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True) # S.No
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))

    # Relationships
    owner = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

class Context(Base):
    # To store context/notes management
    __tablename__ = "contexts"

    id = Column(Integer, primary_key=True, index=True)
    whatsapp_id = Column(String, unique=True, index=True, nullable=False)
    last_action = Column(String, nullable=True) # e.g. "pending_add_confirmation"
    last_data = Column(String, nullable=True)   # JSON string of pending data
    summary = Column(String, nullable=True)     # Conversation summary
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
