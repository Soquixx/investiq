import os
import pickle
import numpy as np
from typing import Dict, Any

class MLEngine:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
        
        # Load all models with the exact filenames from your directory
        self.investor_classifier = self.load_model('risk_model.pkl') or self.load_model('investor_classifier.pkl')
        self.asset_allocator = self.load_model('asset_allocation (1).pkl')
        self.return_predictor = self.load_model('return_prediction.pkl')
        self.scaler_risk = self.load_model('scaler_risk.pkl')
        self.scaler_ret = self.load_model('scaler_ret.pkl')
        self.scaler_alloc = self.load_model('scaler_alloc.pkl')
        self.le_risk = self.load_model('le_risk.pkl')
        print(f"✅ ML Engine initialized (Risk Model: {'risk_model.pkl' if self.investor_classifier else 'None'})")

    def load_model(self, filename):
        full_path = os.path.join(self.model_path, filename)
        if os.path.exists(full_path):
            with open(full_path, 'rb') as f:
                return pickle.load(f)
        return None

    def _apply_scaling(self, scaler, data, features):
        """Scale data using the provided scaler and ensure feature names match if available"""
        if not scaler:
            return data
        
        # If the scaler has feature names, we should try to use them or at least match the count
        try:
            
            expected_n = getattr(scaler, 'n_features_in_', data.shape[1])
            if data.shape[1] != expected_n:
                # If mismatch, try to slice 
                data = data[:, :expected_n]
            
            return scaler.transform(data)
        except Exception as e:
            print(f"Scaling error: {e}")
            return data

    def generate_analysis(self, age, income, risk_score, horizon, amount, expenses=0, occupation_enc=1):
        try:
            # Short-circuit if no models at all (rare)
            if not self.investor_classifier:
                 investor_type = 'Moderate'
            else:
                 # 1. Investor Classification
                 # Mapping horizon to numeric encoding
                 horizon_enc = 0
                 if horizon >= 10: horizon_enc = 2
                 elif horizon >= 3: horizon_enc = 1

                 monthly_income = income / 12
                 feat_classifier = np.array([[float(age), float(monthly_income), float(expenses), float(amount), float(horizon_enc), float(occupation_enc)]])
                 risk_input = self._apply_scaling(self.scaler_risk, feat_classifier, None)
                 prediction = self.investor_classifier.predict(risk_input)[0]
                 investor_type = prediction if isinstance(prediction, str) else (self.le_risk.inverse_transform([prediction])[0] if self.le_risk else prediction)

            # 2. Return Prediction Fallback
            if self.return_predictor:
                feat_ret = np.array([[float(age)]])
                ret_input = self._apply_scaling(self.scaler_ret, feat_ret, None)
                predicted_return = float(self.return_predictor.predict(ret_input)[0])
            else:
                # Rule-based return estimation
                predicted_return = 12.0 # Standard Indian equity-oriented return

            # 3. Asset Allocation Fallback
            if self.asset_allocator:
                feat_alloc = np.array([[float(age)]])
                alloc_input = self._apply_scaling(self.scaler_alloc, feat_alloc, None)
                raw_weights = self.asset_allocator.predict(alloc_input)[0]
                # Softmax
                exp_w = np.exp(raw_weights - np.max(raw_weights))
                normalized = (exp_w / exp_w.sum()) * 100
                model_labels = ["Large Cap Stocks", "Mid Cap Stocks", "Debt Funds", "Gold", "Cash Equivalents"]
                raw_alloc = {l: v for l, v in zip(model_labels, normalized)}
                equity = raw_alloc.get("Large Cap Stocks", 0) + raw_alloc.get("Mid Cap Stocks", 0)
                debt = raw_alloc.get("Debt Funds", 0)
                gold = raw_alloc.get("Gold", 0)
                m_funds = raw_alloc.get("Cash Equivalents", 0) * 0.7
                cash = raw_alloc.get("Cash Equivalents", 0) * 0.3
            else:
                # Optimized Rule-based allocation for Indian context
                equity_base = min(75, max(20, 100 - age)) # Cap equity at 75% for fallback
                equity = equity_base
                debt = (100 - equity_base) * 0.5
                gold = 10.0
                m_funds = (100 - equity_base - gold) * 0.3
                cash = max(5.0, 100 - (equity + debt + gold + m_funds))

            # RISK ADJUSTMENT LAYER
            # risk_score is 1-10. 5 is neutral.
            risk_factor = (risk_score - 5) * 5 
            if risk_factor > 0:
                shift = (debt * (risk_factor / 100))
                equity += shift
                debt -= shift
            elif risk_factor < 0:
                shift = (equity * (abs(risk_factor) / 100))
                debt += shift
                equity -= shift

            # Final check and 100% normalization
            final_allocation = {
                "Equity": max(5, equity),
                "Debt": max(5, debt),
                "Gold": max(2, gold),
                "Mutual Funds": max(5, m_funds),
                "Cash/SIP": max(3.0, cash) # Ensuring floor for cash
            }
            
            total = sum(final_allocation.values())
            allocation_pct = {k: round((v / total) * 100, 2) for k, v in final_allocation.items()}
            
            # Re-normalize to exactly 100.0
            diff = 100.0 - sum(allocation_pct.values())
            if abs(diff) > 0:
                allocation_pct["Equity"] = round(allocation_pct["Equity"] + diff, 2)
                
            # Calculate amounts
            allocation_amt = {k: round((v / 100) * amount, 2) for k, v in allocation_pct.items()}
                
            # Weighted average calculation as a sanity check
            # Benchmarks: Equity 15%, Debt 7%, Gold 8%, MF 11%, Cash 5%
            calculated_return = sum((allocation_pct.get(k, 0) / 100) * v for k, v in {
                'Equity': 15.0, 'Debt': 7.0, 'Gold': 8.0, 'Mutual Funds': 11.0, 'Cash/SIP': 5.0
            }.items())

            # Final Return Prediction: Use model but cap it at 18% 
            final_return = predicted_return if (0 < predicted_return < 25.0) else calculated_return
            final_return = min(18.0, max(5.0, final_return))

            return {
                "ml_powered": self.asset_allocator is not None,
                "investor_type": str(investor_type),
                "risk_level": "high" if allocation_pct.get('Equity', 0) > 55 else ("low" if allocation_pct.get('Equity', 0) < 25 else "medium"),
                "suitability_status": "High" if horizon >= 10 else ("Moderate" if horizon >= 3 else "Low"),
                "allocation_percentage": allocation_pct,
                "allocation_amount": allocation_amt,
                "expected_annual_return_percentage": round(final_return, 2),
                "investment_amount": amount,
                "investment_horizon": horizon
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"MLEngine critical failure: {e}")
            return {"error": str(e), "ml_powered": False}
