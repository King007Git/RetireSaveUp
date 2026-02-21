import math
from src.schema.returnCalcSchema import ReturnsInput, ReturnsResponse, SavingsByDate

def calculate_tax(income: float) -> float:
    """Calculates income tax based on the simplified slabs provided."""
    tax = 0.0
    if income > 1500000:
        tax += (income - 1500000) * 0.30
        income = 1500000
    if income > 1200000:
        tax += (income - 1200000) * 0.20
        income = 1200000
    if income > 1000000:
        tax += (income - 1000000) * 0.15
        income = 1000000
    if income > 700000:
        tax += (income - 700000) * 0.10
    return tax

def process_returns(payload: ReturnsInput, investment_type: str) -> ReturnsResponse:
    """Core engine for processing transactions, periods, and calculating financial returns."""
    annual_income = payload.wage * 12
    t_years = max(60 - payload.age, 5) 
    inflation_rate = payload.inflation / 100.0
    
    interest_rate = 0.0711 if investment_type == "nps" else 0.1449
    
    total_tx_amount = 0.0
    total_tx_ceiling = 0.0
    
    processed_txs = []
    seen_dates = set()
    
    for tx in payload.transactions:
        if tx.amount < 0 or tx.date in seen_dates:
            continue
            
        seen_dates.add(tx.date)
        
        ceiling = math.ceil(tx.amount / 100.0) * 100.0
        total_tx_amount += tx.amount
        total_tx_ceiling += ceiling
        
        remanent = ceiling - tx.amount
        
        applicable_qs = [(i, q) for i, q in enumerate(payload.q) if q.start <= tx.date <= q.end]
        if applicable_qs:
            best_q = sorted(applicable_qs, key=lambda x: (x[1].start, -x[0]), reverse=True)[0][1]
            remanent = best_q.fixed
            
        remanent += sum(p.extra for p in payload.p if p.start <= tx.date <= p.end)
        processed_txs.append({"date": tx.date, "final_remanent": remanent})

    savings_list = []
    
    for k_period in payload.k:
        invested_amount = sum(
            tx["final_remanent"] for tx in processed_txs 
            if k_period.start <= tx["date"] <= k_period.end
        )
        
        a_final = invested_amount * math.pow((1 + interest_rate), t_years)
        a_real = a_final / math.pow((1 + inflation_rate), t_years)
        profit = a_real - invested_amount
        
        tax_benefit = 0.0
        if investment_type == "nps":
            nps_deduction = min(invested_amount, annual_income * 0.10, 200000.0)
            normal_tax = calculate_tax(annual_income)
            discounted_tax = calculate_tax(annual_income - nps_deduction)
            tax_benefit = normal_tax - discounted_tax

        savings_list.append(
            SavingsByDate(
                start=k_period.start,
                end=k_period.end,
                amount=round(invested_amount, 2),
                profit=round(profit, 2),
                taxBenefit=round(tax_benefit, 2)
            )
        )
        
    return ReturnsResponse(
        totalTransactionAmount=round(total_tx_amount, 2),
        totalCeiling=round(total_tx_ceiling, 2),
        savingsByDates=savings_list
    )