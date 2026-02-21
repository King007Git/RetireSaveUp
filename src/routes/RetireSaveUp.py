from fastapi import APIRouter, Depends
import math
from typing import List
from typing import Set
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from config import settings
from src.connection.session import get_db
from src.models.userModel import User
from src.models.history import CalculationHistory, CalculationHistoryResponse
from src.schema.transactions import (
    TransactionParsed,
    ExpenseInput, 
    InvalidTransaction, 
    ValidatorInput, 
    ValidatorResponse,
    FilteredTransaction,
    FilterResponse,
    FilterInput,
    InvalidFilteredTransaction
)
from src.schema.returnCalcSchema import (
    ReturnsResponse,
    ReturnsInput
)
from src.services.returnCalcServices import process_returns
from src.utils import get_current_user

router = APIRouter(
    prefix=f"/blackrock/challenge/{settings.VERSION}",
    tags=['retireSaveUP']
)

@router.post("/transactions:parse", 
    response_model=List[TransactionParsed]
)
async def parse_transactions(expenses: List[ExpenseInput]):
    
    parsed_transactions = []
    
    for expense in expenses:
        ceiling_val = math.ceil(expense.amount / 100.0) * 100.0
        remanent_val = ceiling_val - expense.amount
        
        parsed_transactions.append(
            TransactionParsed(
                date=expense.date,
                amount=expense.amount,
                ceiling=ceiling_val,
                remanent=remanent_val
            )
        )
        
    return parsed_transactions

@router.post(
    "/transactions:validator",
    response_model=ValidatorResponse
)
async def validate_transactions(payload: ValidatorInput):
    valid_transactions: List[TransactionParsed] = []
    invalid_transactions: List[InvalidTransaction] = []
    
    # Use a set for O(1) time complexity when checking for duplicate dates
    seen_dates: Set[str] = set()
    
    for tx in payload.transactions:
        is_valid = True
        error_message = ""
        
        # Rule 1: No negative amounts or negative remanents
        if tx.amount < 0 or tx.remanent < 0 or tx.ceiling < tx.amount:
            is_valid = False
            error_message = "Negative amounts are not allowed"
            
        # Rule 2: No duplicate timestamps
        elif tx.date in seen_dates:
            is_valid = False
            error_message = "Duplicate transaction"
            
        # Rule 3: Hard constraint from the mathematical limits (x < 500,000)
        elif tx.amount >= 500000:
            is_valid = False
            error_message = "Amount exceeds maximum allowed limit"
            
        # Optional Rule 4: Ensuring transaction doesn't exceed the user's wage logically
        elif tx.amount > payload.wage:
             is_valid = False
             error_message = "Transaction amount exceeds recorded wage"

        # Route the transaction to the correct output list
        if is_valid:
            valid_transactions.append(tx)
            seen_dates.add(tx.date) # Mark this date as seen
        else:
            invalid_transactions.append(
                InvalidTransaction(
                    date=tx.date,
                    amount=tx.amount,
                    ceiling=tx.ceiling,
                    remanent=tx.remanent,
                    message=error_message
                )
            )
            
    return ValidatorResponse(
        valid=valid_transactions,
        invalid=invalid_transactions
    )

@router.post(
    "/transactions:filter",
    response_model=FilterResponse
)
async def filter_transactions(payload: FilterInput):
    """
    Validates transactions against q, p, and k period rules to determine 
    the final modified remanent to be invested.
    """
    valid_txs: List[FilteredTransaction] = []
    invalid_txs: List[InvalidFilteredTransaction] = []
    seen_dates: Set[str] = set()
    
    for tx in payload.transactions:
        # --- Base Validations ---
        if tx.amount < 0:
            invalid_txs.append(
                InvalidFilteredTransaction(date=tx.date, amount=tx.amount, message="Negative amounts are not allowed")
            )
            continue
            
        if tx.date in seen_dates:
            invalid_txs.append(
                InvalidFilteredTransaction(date=tx.date, amount=tx.amount, message="Duplicate transaction")
            )
            continue
            
        seen_dates.add(tx.date)
        
        # Step 1: Calculate initial ceiling and remanent
        current_ceiling = math.ceil(tx.amount / 100.0) * 100.0
        current_remanent = current_ceiling - tx.amount
        
        # Step 2: Apply Q Rules (Fixed Amount Override)
        applicable_qs = []
        for index, q in enumerate(payload.q):
            if q.start <= tx.date <= q.end:
                applicable_qs.append((index, q))
                
        if applicable_qs:
            # Find the Q period with the latest start date. 
            # On a tie, the lower original index (first in list) wins.
            best_q = None
            best_start = ""
            best_idx = float('inf')
            
            for idx, q in applicable_qs:
                if q.start > best_start:
                    best_q = q
                    best_start = q.start
                    best_idx = idx
                elif q.start == best_start and idx < best_idx:
                    best_q = q
                    best_idx = idx
            
            # Override remanent with the fixed amount
            current_remanent = best_q.fixed
            
        # Step 3: Apply P Rules (Extra Amount Addition)
        extra_sum = sum(
            p.extra for p in payload.p 
            if p.start <= tx.date <= p.end
        )
        current_remanent += extra_sum
        
        # Step 4: Group by K Periods
        in_k_period = any(
            k.start <= tx.date <= k.end 
            for k in payload.k
        )
        
        # Build the final valid transaction
        final_tx = FilteredTransaction(
            date=tx.date,
            amount=tx.amount,
            ceiling=current_ceiling,
            remanent=current_remanent
        )
        
        # The PDF example only attaches 'inkPeriod' if it is true
        if in_k_period:
            final_tx.inkPeriod = True
            
        valid_txs.append(final_tx)

    return FilterResponse(valid=valid_txs, invalid=invalid_txs)

@router.post(
    "/returns:nps", 
    response_model=ReturnsResponse
)
async def calculate_nps_returns(
    payload: ReturnsInput, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Perform the calculation
    result = process_returns(payload, investment_type="nps")
    
    # 2. Create the history record
    history_record = CalculationHistory(
        user_id=current_user.id,
        investment_type="nps",
        # Convert Pydantic models to dictionaries for JSONB storage
        payload=payload.model_dump(), 
        result=result.model_dump()
    )
    
    # 3. Save to database
    db.add(history_record)
    await db.commit()
    
    return result

@router.post(
    "/returns:index", 
    response_model=ReturnsResponse
)
async def calculate_index_returns(
    payload: ReturnsInput, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Perform the calculation
    result = process_returns(payload, investment_type="index")
    
    # 2. Create the history record
    history_record = CalculationHistory(
        user_id=current_user.id,
        investment_type="index",
        # Convert Pydantic models to dictionaries for JSONB storage
        payload=payload.model_dump(), 
        result=result.model_dump()
    )
    
    # 3. Save to database
    db.add(history_record)
    await db.commit()
    
    return result

@router.get(
    "/history", 
    response_model=List[CalculationHistoryResponse]
)
async def get_user_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Build the query to filter by the authenticated user's ID
    statement = (
        select(CalculationHistory)
        .where(CalculationHistory.user_id == current_user.id)
        .order_by(CalculationHistory.created_at.desc())
    )
    
    # 2. Execute the query
    result = await db.exec(statement)
    history_records = result.all()
    
    # 3. Return the list of records
    return history_records