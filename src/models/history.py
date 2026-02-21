import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel

class CalculationHistory(SQLModel, table=True):
    __tablename__ = "calculation_history"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    investment_type: str = Field(description="Will be 'nps' or 'index'")
    
    payload: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    result: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CalculationHistoryResponse(BaseModel):
    id: uuid.UUID
    investment_type: str
    payload: dict
    result: dict
    created_at: datetime
