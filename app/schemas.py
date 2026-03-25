from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

# --- Categories ---
class CategoryBase(BaseModel):
    name: str
    type: str # 'income' or 'expense'

class CategoryCreate(CategoryBase):
    pass

class CategoryOut(CategoryBase):
    id: int

    class Config:
        from_attributes = True

# --- Users ---
class UserBase(BaseModel):
    whatsapp_id: str
    name: Optional[str] = None
    timezone: Optional[str] = "UTC"

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Transactions ---
class TransactionBase(BaseModel):
    amount: float
    description: Optional[str] = None
    date: date

class TransactionCreate(TransactionBase):
    user_id: int
    category_id: int

class TransactionOut(TransactionBase):
    id: int
    user_id: int
    category: CategoryOut

    class Config:
        from_attributes = True

# --- Tool Schemas for LLM Extraction ---
class AddTransactionSchema(BaseModel):
    amount: float = Field(..., description="The exact transaction amount extracted from the message")
    category: str = Field(..., description="The category for the transaction (e.g. Food, Salary, Rent, Transport)")
    type: str = Field(..., description="Transaction type, must be 'income' or 'expense'")
    description: str = Field(..., description="Short description of the transaction")
    date: str = Field(..., description="The exact date the transaction occurred in YYYY-MM-DD format based on the user's current date context.")

class RemoveTransactionSchema(BaseModel):
    s_no: int = Field(..., description="The S.No (ID) of the database entry to remove")

class EditTransactionSchema(BaseModel):
    s_no: int = Field(..., description="The S.No (ID) of the transaction to edit")
    field_to_edit: str = Field(..., description="The field to edit. One of 'amount', 'description', 'date', 'category'")
    new_value: str = Field(..., description="The new value to set for the field")

class FindTransactionSchema(BaseModel):
    query: str = Field(..., description="The search query, which could be proximity to a date, specific names, amounts, or categories")

class FilterTransactionSchema(BaseModel):
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")
    category: Optional[str] = Field(None, description="Category to filter by")
