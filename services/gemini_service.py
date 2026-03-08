import os
import logging
import json
import requests
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.endpoint = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
        
        if not self.api_key:
            logger.info("GEMINI_API_KEY missing.")
        else:
            logger.info("Gemini API v1 stable ready.")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_investment_analysis(self, **kwargs) -> Dict[str, Any]:
        if not self.is_available():
            return self._rule_based_analysis({}, {}, {})
        
        #prompt
        context_parts = []
        for key, value in kwargs.items():
            if value:
                context_parts.append(f"{key.upper()}:\n{json.dumps(value, indent=2)}")
        
        context_str = "\n\n".join(context_parts)
        
        prompt = f"""
        Act as a professional Indian Financial Advisor with deep expertise in SEBI guidelines and Indian market dynamics (NSE/BSE).
        Analyze the following context derived from our ML engine and user profile to provide HIGHLY PERSONALIZED advice.
        
        CONTEXT:
        {context_str}
        
        INSTRUCTIONS:
        1. Contextual Summary: Briefly explain WHY this portfolio was chosen based on the user's age, risk tolerance, and current market sentiment.
        2. Key Insights: Provide 3-4 specific insights. Mention specific asset classes (e.g., Equity, Gold) and why their weightage is appropriate now.
        3. Identified Risks: Note at least 2 specific risks for THIS profile (e.g., high equity exposure for a short horizon).
        4. Action Plan: Provide 3 clear, actionable steps the user should take today.
        
        CONSTRAINTS:
        - Tone: Professional, authoritative yet accessible.
        - Format: Return ONLY a valid JSON object.
        - DO NOT use generic advice. Reference the specific percentages and amounts provided in the context.
        
        Expected JSON Structure:
        {{
            "summary": "...",
            "key_insights": ["...", "...", "..."],
            "risks": ["...", "..."],
            "actions": ["...", "...", "..."],
            "confidence": 0-100
        }}
        """

        try:
            url = f"{self.endpoint}?key={self.api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            response = requests.post(url, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                raw_text = data['candidates'][0]['content']['parts'][0]['text']
                
                # Robust JSON extraction
                json_match = raw_text.strip()
                if "```json" in json_match:
                    json_match = json_match.split("```json")[1].split("```")[0]
                elif "```" in json_match:
                    json_match = json_match.split("```")[1].split("```")[0]
                
                analysis = json.loads(json_match.strip())
                
                return {
                    **analysis,
                    "source": "Gemini 1.5 Pro AI",
                    "is_fallback": False,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Gemini API dynamic error: {e}")
        
        return self._rule_based_analysis(kwargs.get('allocation', {}), kwargs.get('user_profile', {}), kwargs.get('market_data', {}))

    def generate_xai_reasoning(self, user_profile: Dict, allocation: Dict, market_data: Dict) -> Dict[str, str]:
        """
        XAI layer: Justify recommendations using the
        'Because [Market Trend] + [User Need] = [Logic]' framework.
        Returns three pillars: user_fit, allocation_gap, market_context.
        """
        risk          = user_profile.get('risk_tolerance', 'medium').lower()
        horizon       = user_profile.get('investment_horizon', 'medium').lower()
        investor_type = allocation.get('investor_type', f'{risk.title()} Profile')
        alloc_pct     = allocation.get('allocation_percentage', {})
        equity_pct    = alloc_pct.get('Equity', alloc_pct.get('stocks', 0))
        debt_pct      = alloc_pct.get('Debt', alloc_pct.get('bonds', 0))
        gold_pct      = alloc_pct.get('Gold', alloc_pct.get('gold', 0))
        sentiment     = market_data.get('sentiment', {}).get('sentiment', 'neutral') if isinstance(market_data.get('sentiment'), dict) else str(market_data.get('sentiment', 'neutral'))
        exp_return    = allocation.get('expected_annual_return_percentage', 'N/A')

        if self.is_available():
            prompt = f"""You are an Explainable AI (XAI) Financial Analyst. Justify an investment recommendation in EXACTLY three sentences using the framework below. Be concise (max 150 tokens total).

FRAMEWORK:
1. User Fit: Why the allocation matches this investor's risk tolerance and goals.
2. Allocation Gap: The specific equity/debt/gold split and what that means for return vs. risk.
3. Market Context: One sentence on real-time market conditions influencing this call.

DATA:
- Investor Type: {investor_type}
- Risk Tolerance: {risk} | Horizon: {horizon}
- Allocation: Equity {equity_pct}%, Debt {debt_pct}%, Gold {gold_pct}%
- Expected Annual Return: {exp_return}%
- Market Sentiment: {sentiment}

Return ONLY a JSON object — no markdown, no extra keys:
{{"user_fit": "...", "allocation_gap": "...", "market_context": "..."}}"""
            try:
                url = f"{self.endpoint}?key={self.api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                response = requests.post(url, json=payload, timeout=12)
                if response.status_code == 200:
                    raw = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                    if "```" in raw:
                        raw = raw.split("```")[1].split("```")[0]
                        if raw.startswith("json"):
                            raw = raw[4:]
                    result = json.loads(raw.strip())
                    if all(k in result for k in ('user_fit', 'allocation_gap', 'market_context')):
                        return result
            except Exception as e:
                logger.warning(f"XAI Gemini call failed: {e}")

        return self._xai_fallback(risk, horizon, equity_pct, debt_pct, gold_pct, sentiment, exp_return)

    def _xai_fallback(self, risk, horizon, equity_pct, debt_pct, gold_pct, sentiment, exp_return) -> Dict[str, str]:
        """Deterministic XAI explanation when Gemini is unavailable."""
        risk_desc = {'low': 'capital preservation', 'medium': 'balanced growth', 'high': 'maximum wealth creation'}
        horizon_desc = {'short': 'short-term (1-2 yr)', 'medium': 'medium-term (3-5 yr)', 'long': 'long-term (10+ yr)'}
        goal = risk_desc.get(risk, 'balanced growth')
        hor  = horizon_desc.get(horizon, 'medium-term')

        user_fit = (
            f"Because you have a {risk}-risk tolerance targeting {goal} over a {hor} horizon, "
            f"this portfolio is calibrated to deliver an estimated {exp_return}% annual return "
            f"without overexposing you to volatile assets."
        )
        allocation_gap = (
            f"Because your suggested allocation holds {equity_pct:.0f}% Equity, {debt_pct:.0f}% Debt, "
            f"and {gold_pct:.0f}% Gold, the equity weight is set to drive growth while debt and "
            f"gold act as stabilisers — balancing upside with downside protection."
        )
        sentiment_map = {
            'bullish': 'positive market momentum supports higher equity exposure right now',
            'bearish': 'cautious market conditions justify increased allocation to defensive assets like Debt and Gold',
            'neutral': 'sideways market conditions favour a diversified, all-weather allocation strategy'
        }
        market_context = (
            f"Because current Indian market sentiment is {sentiment}, "
            + sentiment_map.get(sentiment.lower(), 'market conditions support this balanced allocation') + "."
        )
        return {"user_fit": user_fit, "allocation_gap": allocation_gap, "market_context": market_context}

    def _rule_based_analysis(self, allocation, user_profile, market_data):
        """Deterministic fallback when AI is unavailable"""
        risk = user_profile.get('risk_tolerance', 'medium').lower()
        
        fallbacks = {
            'low': {
                'summary': "Conservative strategy focused on capital preservation and steady returns through debt and gold.",
                'insights': ["Higher allocation to Debt for stability", "Gold acts as an inflation hedge", "Minimal equity prevents large drawdowns"],
                'risks': ["Inflation risk", "Lower long-term growth potential"],
                'actions': ["Identify high-quality debt funds", "Set up monthly SIP in Gold", "Maintain emergency fund in liquid cash"]
            },
            'medium': {
                'summary': "Balanced growth strategy aiming for moderate returns with controlled volatility.",
                'insights': ["Equity-Debt mix provides best risk-adjusted returns", "Diversification across 5 asset classes", "Adaptable to most market conditions"],
                'risks': ["Moderate market volatility", "Interest rate fluctuations"],
                'actions': ["Rebalance semi-annually", "Diversify via Index Funds", "Continue disciplined SIPs"]
            },
            'high': {
                'summary': "Aggressive wealth creation strategy focused on maximum long-term equity growth.",
                'insights': ["High Equity exposure for maximum compounding", "Small allocation to Gold for diversification", "Focus on Mid/Small cap opportunities"],
                'risks': ["Significant short-term volatility", "Market correction impact"],
                'actions': ["Focus on long-term time horizon", "Avoid panic selling during dips", "Aggressive SIP in growth funds"]
            }
        }
        
        f = fallbacks.get(risk, fallbacks['medium'])
        
        return {
            "summary": f['summary'],
            "key_insights": f['insights'],
            "risks": f['risks'],
            "actions": f['actions'],
            "source": "Deterministic Rule Engine (AI Offline)",
            "is_fallback": True,
            "timestamp": datetime.now().isoformat()
        }
