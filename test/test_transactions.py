import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_parse_transactions_success():
    """Tests if the ceiling and remanent math is calculated correctly."""
    payload = [
        {"date": "2021-10-01 20:15:00", "amount": 1519.0},
        {"date": "2023-10-12 20:15:30", "amount": 250.0}
    ]
    
    response = client.post("/blackrock/challenge/v1/transactions:parse", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    # Check first expense math (from the PDF example) [cite: 13]
    assert data[0]["amount"] == 1519.0
    assert data[0]["ceiling"] == 1600.0
    assert data[0]["remanent"] == 81.0
    
    # Check second expense math [cite: 117]
    assert data[1]["amount"] == 250.0
    assert data[1]["ceiling"] == 300.0
    assert data[1]["remanent"] == 50.0

def test_parse_transactions_invalid_date_format():
    """Tests if Pydantic blocks incorrect date formats."""
    payload = [
        # Missing time component
        {"date": "2021-10-01", "amount": 1519.0} 
    ]
    
    response = client.post("/blackrock/challenge/v1/transactions:parse", json=payload)
    
    # Should fail Pydantic validation with 422 Unprocessable Entity
    assert response.status_code == 422

def test_validator_separates_valid_and_invalid():
    """Tests if the validator correctly applies negative amount and duplicate rules."""
    payload = {
        "wage": 50000,
        "transactions": [
            # Valid transaction
            {"date": "2023-01-15 10:30:00", "amount": 2000.0, "ceiling": 2100.0, "remanent": 100.0},
            
            # Duplicate transaction (same date as above) [cite: 335, 369]
            {"date": "2023-01-15 10:30:00", "amount": 250.0, "ceiling": 300.0, "remanent": 50.0},
            
            # Invalid: Negative amount [cite: 339-341, 372]
            {"date": "2023-12-17 08:09:45", "amount": -480.0, "ceiling": -400.0, "remanent": 80.0},
            
            # Invalid: Illogical dummy data (ceiling < amount implies negative remanent) [cite: 281-288, 303-305]
            {"date": "2023-07-10 09:15:00", "amount": 250.0, "ceiling": 200.0, "remanent": 30.0}
        ]
    }
    
    response = client.post("/blackrock/challenge/v1/transactions:validator", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # We should have 1 valid and 3 invalid transactions
    assert len(data["valid"]) == 1
    assert len(data["invalid"]) == 3
    
    # Check if the valid transaction is the correct one
    assert data["valid"][0]["amount"] == 2000.0
    
    # Check the exact error messages required by the document
    invalid_messages = [item["message"] for item in data["invalid"]]
    assert "Duplicate transaction" in invalid_messages 
    assert "Negative amounts are not allowed" in invalid_messages

def test_filter_transactions_period_logic():
    """Tests the complex application of Q (override), P (addition), and K (grouping) rules."""
    # Using the exact example payload from the challenge document
    payload = {
        "q": [{"fixed": 0.0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
        "p": [{"extra": 25.0, "start": "2023-10-01 08:00:00", "end": "2023-12-31 19:59:59"}],
        "k": [
            {"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"},
            {"start": "2023-03-01 00:00:00", "end": "2023-11-30 23:59:59"}
        ],
        "wage": 50000,
        "transactions": [
            {"date": "2023-02-28 15:49:20", "amount": 375.0},
            {"date": "2023-07-01 21:59:00", "amount": 620.0},
            {"date": "2023-10-12 20:15:30", "amount": 250.0},
            {"date": "2023-12-17 08:09:45", "amount": 480.0}
        ]
    }
    
    response = client.post("/blackrock/challenge/v1/transactions:filter", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["valid"]) == 4
    assert len(data["invalid"]) == 0
    
    # 1. Test normal calculation (No Q, No P)
    # 375 -> ceiling 400 -> remanent 25
    tx_feb = next(t for t in data["valid"] if t["date"] == "2023-02-28 15:49:20")
    assert tx_feb["remanent"] == 25.0
    assert tx_feb["inkPeriod"] is True
    
    # 2. Test Q Rule Override 
    # 620 -> normally remanent 80, but Q rule overrides to 0
    tx_jul = next(t for t in data["valid"] if t["date"] == "2023-07-01 21:59:00")
    assert tx_jul["remanent"] == 0.0
    
    # 3. Test P Rule Addition
    # 250 -> normally remanent 50, but P rule adds 25 = 75
    tx_oct = next(t for t in data["valid"] if t["date"] == "2023-10-12 20:15:30")
    assert tx_oct["remanent"] == 75.0
    
    # 4. Test P Rule Addition on a different transaction
    # 480 -> normally remanent 20, but P rule adds 25 = 45
    tx_dec = next(t for t in data["valid"] if t["date"] == "2023-12-17 08:09:45")
    assert tx_dec["remanent"] == 45.0

def test_filter_transactions_invalid_handling():
    """Tests if the filter endpoint correctly rejects duplicates and negatives."""
    payload = {
        "q": [], "p": [], "k": [], "wage": 50000,
        "transactions": [
            {"date": "2023-10-12 20:15:30", "amount": 250.0},
            {"date": "2023-10-12 20:15:30", "amount": 250.0}, # Duplicate
            {"date": "2023-12-17 08:09:45", "amount": -480.0}  # Negative
        ]
    }
    
    response = client.post("/blackrock/challenge/v1/transactions:filter", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["valid"]) == 1
    assert len(data["invalid"]) == 2
    
    invalid_messages = [item["message"] for item in data["invalid"]]
    assert "Duplicate transaction" in invalid_messages
    assert "Negative amounts are not allowed" in invalid_messages

def test_returns_nps_calculation_logic():
    """Tests the NPS returns calculation, including tax benefits, compound interest, and inflation."""
    # This payload is taken exactly from the challenge document example (Pages 12-13)
    payload = {
        "age": 29,
        "wage": 50000,
        "inflation": 5.5,
        "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
        "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-31 19:59:59"}],
        "k": [
            {"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"},
            {"start": "2023-03-01 00:00:00", "end": "2023-11-30 23:59:59"} # Adjusted 11-31 to 11-30 as Nov has 30 days
        ],
        "transactions": [
            {"date": "2023-02-28 15:49:20", "amount": 375},
            {"date": "2023-07-01 21:59:00", "amount": 620},
            {"date": "2023-10-12 20:15:30", "amount": 250},
            {"date": "2023-12-17 08:09:45", "amount": 480},
            {"date": "2023-12-17 08:09:45", "amount": 10} # This is a duplicate date! It should be ignored.
        ]
    }
    
    response = client.post("/blackrock/challenge/v1/returns:nps", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check global totals [cite: 424-425]
    # The duplicate transaction (10) should be ignored, meaning total is 1725, not 1735.
    assert data["totalTransactionAmount"] == 1725.0
    assert data["totalCeiling"] == 1900.0
    
    # Check savings and returns for the full year K-period [cite: 429-433]
    full_year = next(k for k in data["savingsByDates"] if k["start"] == "2023-01-01 00:00:00")
    assert full_year["amount"] == 145.0
    assert full_year["profit"] == 86.88
    assert full_year["taxBenefit"] == 0.0 # Wage is 50k/mo = 6L/yr, which is in the 0% tax slab
    
    # Check savings and returns for the partial year K-period [cite: 435-439]
    partial_year = next(k for k in data["savingsByDates"] if k["start"] == "2023-03-01 00:00:00")
    assert partial_year["amount"] == 75.0
    assert partial_year["profit"] == 44.94

def test_returns_index_calculation_logic():
    """Tests that the Index fund calculates aggressive returns without applying tax rebates."""
    payload = {
        "age": 29,
        "wage": 50000,
        "inflation": 5.5,
        "q": [], "p": [],
        "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
        "transactions": [
            {"date": "2023-10-12 20:15:30", "amount": 250.0} # Remanent = 50.0
        ]
    }
    
    response = client.post("/blackrock/challenge/v1/returns:index", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    savings = data["savingsByDates"][0]
    
    # 1. Tax Benefit MUST be 0.0 for Index Funds regardless of wage [cite: 447]
    assert savings["taxBenefit"] == 0.0
    
    # 2. Assert that the profit calculated is strictly positive (compound interest applied)
    assert savings["profit"] > 0