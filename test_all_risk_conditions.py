from services.ml_engine import MLEngine
import pandas as pd

def test_all_risk_conditions():
    ml = MLEngine()
    
    # Test cases to find different risk levels
    # Primary drivers in MLEngine: age 

    
    scenarios = [
        {"name": "Scenario 1: High Risk (Young, High Risk Tolerance)", "age": 22, "risk_score": 10, "horizon": 15, "amount": 500000},
        {"name": "Scenario 2: Medium Risk (Middle Age, Balanced)", "age": 45, "risk_score": 5, "horizon": 7, "amount": 500000},
        {"name": "Scenario 3: Low Risk (Elderly, Conservative)", "age": 75, "risk_score": 1, "horizon": 2, "amount": 500000},
        # Adding a few more to be sure we hit the boundaries
        {"name": "Scenario 4: High Risk (Young, Moderate Risk)", "age": 25, "risk_score": 6, "horizon": 10, "amount": 500000},
        {"name": "Scenario 5: Low Risk (Middle Age, Very Conservative)", "age": 40, "risk_score": 1, "horizon": 2, "amount": 500000},
    ]
    
    results = []
    
    print("-" * 80)
    print(f"{'Scenario Name':<45} | {'Equity %':<10} | {'Risk Level':<10}")
    print("-" * 80)
    
    found_levels = set()
    
    for s in scenarios:
        analysis = ml.generate_analysis(
            age=s['age'], 
            income=1200000, # 1 Lakh/month
            risk_score=s['risk_score'], 
            horizon=s['horizon'], 
            amount=s['amount']
        )
        
        equity = analysis['allocation_percentage']['Equity']
        risk = analysis['risk_level']
        found_levels.add(risk)
        
        print(f"{s['name']:<45} | {equity:<10}% | {risk.upper():<10}")
        results.append({
            "Input": f"Age: {s['age']}, Risk Score: {s['risk_score']}, Horizon: {s['horizon']}yr",
            "Equity": f"{equity}%",
            "Output_Risk": risk.upper()
        })
        
    print("-" * 80)
    print(f"Captured Risk Levels: {found_levels}")

if __name__ == "__main__":
    test_all_risk_conditions()
