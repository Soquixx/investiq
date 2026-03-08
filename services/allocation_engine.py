"""Allocation Engine - Core logic for portfolio generation and ML integration"""
from typing import Dict, Any, List
import logging
from .ml_engine import MLEngine

logger = logging.getLogger(__name__)

class AllocationEngine:
    def __init__(self):
        """Initialize the engine and attempt to load the ML pipeline"""
        try:
            self.ml_engine = MLEngine()
            self.ml_available = True
            logger.info("ML Engine successfully integrated into AllocationEngine")
        except Exception as e:
            self.ml_available = False
            logger.warning(f"ML Engine initialization failed: {e}. Falling back to rules.")

    def generate_allocation(self, 
                            investment_amount: float,
                            risk_tolerance: str,
                            investment_horizon: str,
                            monthly_income: float,
                            monthly_expenses: float,
                            age: int,
                            investment_experience: int = 1,
                            **kwargs) -> Dict[str, Any]:
        """
        Main entry point for generating investment allocations.
        Uses the new multi-model MLEngine pipeline.
        
        Note: UPI analysis is handled separately and should not be passed here.
        """
        
        # Mapping strings to meaningful numeric scores for the ML models
        # Risk: 1-10 scale
        risk_map = {'low': 3, 'medium': 6, 'high': 9}
        # Horizon: mapped to approximate years
        horizon_map = {'short': 2, 'medium': 5, 'long': 12}
        
        risk_score = risk_map.get(risk_tolerance.lower(), 6)
        horizon_years = horizon_map.get(investment_horizon.lower(), 5)
        
        # The model expects ANNUAL income for better normalization
        annual_income = monthly_income * 12

        if self.ml_available:
            try:
                # Call the new generate_analysis method in MLEngine
                ml_result = self.ml_engine.generate_analysis(
                    age=age,
                    income=annual_income,
                    risk_score=risk_score,
                    horizon=horizon_years,
                    amount=investment_amount,
                    expenses=monthly_expenses,
                    occupation_enc=kwargs.get('occupation', 1)
                )
                
                if ml_result and "error" not in ml_result:
                    ml_result['original_risk_tolerance'] = risk_tolerance
                    ml_result['original_horizon'] = investment_horizon
                    # Ensure risk_level is dynamic based on Equity exposure
                    equity_pct = ml_result.get('allocation_percentage', {}).get('Equity', 0)
                    ml_result['risk_level'] = "high" if equity_pct > 55 else ("low" if equity_pct < 25 else "medium")
                    return ml_result
                else:
                    logger.error(f"ML Analysis failed: {ml_result.get('error') if ml_result else 'Unknown error'}")
            except Exception as e:
                logger.error(f"ML Processing error: {e}")

        # Fallback to rule-based logic if ML fails or is unavailable
        logger.info("Using rule-based fallback allocation")
        return self._rule_based_allocation(risk_tolerance, investment_amount)

    def _convert_ml_array_to_dict(self, ml_array: List[float]) -> Dict[str, float]:
        """
        FIX: Handles the 3-value output [Stocks, Bonds, Cash/Other] 
        and maps them to the 5 asset classes used in the dashboard.
        """
        if not ml_array or len(ml_array) == 0:
            # Emergency fallback
            return {k: 20.0 for k in ['stocks', 'bonds', 'gold', 'fixed_deposits', 'mutual_funds']}

        # Your model outputs 3 values (likely from a 3-column CSV training set)
        if len(ml_array) == 3:
            s = float(ml_array[0])
            b = float(ml_array[1])
            c = float(ml_array[2])
            
            # Normalize if values are 0-1 (e.g., 0.6 -> 60.0)
            factor = 100.0 if s <= 1.0 else 1.0
            
            return {
                'stocks': s * factor,
                'bonds': b * factor,
                'gold': (c * 0.4) * factor,          
                'fixed_deposits': (c * 0.4) * factor, 
                'mutual_funds': (c * 0.2) * factor    
            }
        
        # If  model actually outputs 5 values
        return {
            'stocks': float(ml_array[0]),
            'bonds': float(ml_array[1]),
            'gold': float(ml_array[2]),
            'fixed_deposits': float(ml_array[3]),
            'mutual_funds': float(ml_array[4])
        }

    def _calculate_expected_return(self, allocation: Dict[str, float]) -> float:
        """Calculate weighted average return based on Indian market benchmarks"""
        returns = {
            'Equity': 15.0, 'Mutual Funds': 12.0, 'Gold': 8.0, 
            'Debt': 7.0, 'Cash/SIP': 6.5
        }
        total_return = sum((allocation.get(asset, 0) / 100) * ret for asset, ret in returns.items())
        return round(total_return, 2)

    def _rule_based_allocation(self, risk: str, amount: float) -> Dict[str, Any]:
        """Simple rule-based fallback logic with Indian market context"""
        allocations = {
            'high': {'Equity': 60, 'Mutual Funds': 20, 'Gold': 10, 'Debt': 5, 'Cash/SIP': 5},
            'medium': {'Equity': 40, 'Mutual Funds': 20, 'Gold': 15, 'Debt': 15, 'Cash/SIP': 10},
            'low': {'Equity': 15, 'Mutual Funds': 10, 'Gold': 20, 'Debt': 30, 'Cash/SIP': 25}
        }
        res = allocations.get(risk.lower(), allocations['medium'])
        
        # Calculate amounts
        allocation_amt = {k: round((v / 100) * amount, 2) for k, v in res.items()}
        
        expected_return = self._calculate_expected_return(res)
        
        return {
            "ml_powered": False,
            "investor_type": f"{risk.title()} Profile",
            "suitability_status": "Suitable",
            "allocation_percentage": res,
            "allocation_amount": allocation_amt,
            "expected_annual_return_percentage": expected_return,
            "investment_amount": amount,
            "risk_level": "high" if res.get('Equity', 0) > 55 else ("low" if res.get('Equity', 0) < 25 else "medium")
        }