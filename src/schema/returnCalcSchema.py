from typing import List, Optional
from pydantic import BaseModel

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

class ReturnsInput(BaseModel):
    age: int
    wage: float
    inflation: float
    q: List[QPeriod] = []
    p: List[PPeriod] = []
    k: List[KPeriod] = []
    transactions: List[TransactionInput]

class SavingsByDate(BaseModel):
    start: str
    end: str
    amount: float
    profit: float
    taxBenefit: float

class ReturnsResponse(BaseModel):
    totalTransactionAmount: float
    totalCeiling: float
    savingsByDates: List[SavingsByDate]