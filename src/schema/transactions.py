from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional

class ExpenseInput(BaseModel):
    date: str 
    # The amount must be a number (double) [cite: 217] and strictly less than 500,000. 
    amount: float = Field(..., ge=0, lt=500000, description="Expense amount")

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Enforces the strict YYYY-MM-DD HH:mm:ss format constraint."""
        try:
            datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
            return v
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY-MM-DD HH:mm:ss")

class TransactionParsed(BaseModel):
    date: str 
    amount: float 
    ceiling: float 
    remanent: float 

class TransactionParsed(BaseModel):
    date: str
    amount: float
    ceiling: float
    remanent: float

class ValidatorInput(BaseModel):
    wage: float
    transactions: List[TransactionParsed]

class InvalidTransaction(TransactionParsed):
    message: str

class ValidatorResponse(BaseModel):
    valid: List[TransactionParsed]
    invalid: List[InvalidTransaction]

class QPeriod(BaseModel):
    fixed: float
    start: str
    end: str

class PPeriod(BaseModel):
    extra: float
    start: str
    end: str

class KPeriod(BaseModel):
    start: str
    end: str

class TransactionInput(BaseModel):
    date: str
    amount: float
    ceiling: Optional[float] = None
    remanent: Optional[float] = None

class FilterInput(BaseModel):
    q: List[QPeriod] = []
    p: List[PPeriod] = []
    k: List[KPeriod] = []
    wage: float
    transactions: List[TransactionInput]

class FilteredTransaction(BaseModel):
    date: str
    amount: float
    ceiling: float
    remanent: float
    inkPeriod: Optional[bool] = None

class InvalidFilteredTransaction(BaseModel):
    date: str
    amount: float
    message: str

class FilterResponse(BaseModel):
    valid: List[FilteredTransaction]
    invalid: List[InvalidFilteredTransaction]