"""Financial Advisory Service - AI-powered personalized financial advice using Gemini API"""
import os
import logging
import json
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import requests

from database.models import (
    AdvisorySession, FinancialAdvisor, FinancialGoal, 
    Portfolio, User, Holding, Transaction
)
from database.db import db
from services.market_data_service import MarketDataService
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class FinancialAdvisoryService:
    """
    Comprehensive financial advisory service using Gemini AI.
    Provides personalized recommendations based on user profile, portfolio, and market conditions.
    """
    
    def __init__(self):
        self.gemini_service = GeminiService()
        self.market_service = MarketDataService()
    
    def get_or_create_advisor(self, user: User) -> FinancialAdvisor:
        """Get or create a financial advisor for user"""
        advisor = FinancialAdvisor.query.filter_by(user_id=user.id).first()
        
        if not advisor:
            advisor = FinancialAdvisor(
                user_id=user.id,
                name="AI Investment Advisor",
                specialization="Wealth Management & Market Analysis"
            )
            db.session.add(advisor)
            db.session.commit()
            logger.info(f"Created new advisor for user {user.id}")
        
        return advisor
    
    # Analysis and planning methods
    
    def conduct_portfolio_review(self, user: User) -> Dict[str, Any]:
        """Conduct comprehensive portfolio review using AI"""
        advisor = self.get_or_create_advisor(user)
        portfolio_data = self._collect_portfolio_data(user)
        user_profile = self._collect_user_profile(user)
        market_data = self._get_market_conditions()
        
        # Use GeminiService directly with rich context
        ai_response = self.gemini_service.get_investment_analysis(
            task="Comprehensive Portfolio Review",
            portfolio_details=portfolio_data,
            investor_profile=user_profile,
            market_context=market_data
        )
        
        session = AdvisorySession(
            user_id=user.id,
            advisor_id=advisor.id,
            session_type="portfolio_review",
            title="Comprehensive Portfolio Review",
            description="AI-powered analysis of your investment portfolio",
            portfolio_value_inr=portfolio_data['total_value'],
            user_risk_profile=user_profile['risk_tolerance'],
            time_horizon=user_profile['investment_horizon'],
            advisor_response=ai_response,
            key_findings=ai_response.get('key_insights', []),
            recommendations=ai_response.get('actions', []),
            action_items=ai_response.get('actions', []),
            confidence_score=ai_response.get('confidence', 85),
            ai_model="gemini-1.5-flash"
        )
        
        db.session.add(session)
        advisor.analysis_count += 1
        db.session.commit()
        
        return {'session_id': session.id, 'analysis': ai_response}

    def get_rebalancing_advice(self, user: User) -> Dict[str, Any]:
        """Get AI-powered portfolio rebalancing recommendations"""
        advisor = self.get_or_create_advisor(user)
        portfolio_data = self._collect_portfolio_data(user)
        user_profile = self._collect_user_profile(user)
        
        ai_response = self.gemini_service.get_investment_analysis(
            task="Portfolio Rebalancing Advice",
            current_allocation=portfolio_data['allocation_percentage'],
            investor_profile=user_profile
        )
        
        session = AdvisorySession(
            user_id=user.id,
            advisor_id=advisor.id,
            session_type="rebalancing",
            title="Portfolio Rebalancing Recommendations",
            advisor_response=ai_response,
            portfolio_value_inr=portfolio_data['total_value'],
            ai_model="gemini-1.5-flash"
        )
        db.session.add(session)
        db.session.commit()
        return {'session_id': session.id, 'analysis': ai_response}

    def get_goal_achievement_plan(self, user: User, goal_id: int) -> Dict[str, Any]:
        """Create AI-powered plan to achieve specific financial goal"""
        advisor = self.get_or_create_advisor(user)
        goal = FinancialGoal.query.filter_by(id=goal_id, user_id=user.id).first()
        if not goal: return {'error': 'Goal not found'}
        
        portfolio_data = self._collect_portfolio_data(user)
        user_profile = self._collect_user_profile(user)
        
        ai_response = self.gemini_service.get_investment_analysis(
            task=f"Achievement Plan for {goal.goal_name}",
            goal_details={
                'name': goal.goal_name,
                'target': goal.target_amount_inr,
                'current': goal.current_amount_inr,
                'deadline': goal.target_date.isoformat()
            },
            current_portfolio=portfolio_data
        )
        
        # Update goal
        goal.monthly_investment_required = ai_response.get('monthly_investment_required', 0)
        
        session = AdvisorySession(
            user_id=user.id,
            advisor_id=advisor.id,
            session_type="goal_setting",
            title=f"Goal Plan: {goal.goal_name}",
            advisor_response=ai_response,
            ai_model="gemini-1.5-flash"
        )
        db.session.add(session)
        db.session.commit()
        return {'session_id': session.id, 'analysis': ai_response}

    # Internal context collectors
    def _collect_portfolio_data(self, user: User) -> Dict[str, Any]:
        portfolios = Portfolio.query.filter_by(user_id=user.id, is_active=True).all()
        total_value = sum(p.get_current_value() for p in portfolios)
        
        allocation = {}
        for p in portfolios:
            for h in p.holdings.all():
                holding_val = h.get_current_value()
                allocation[h.asset_type] = allocation.get(h.asset_type, 0) + holding_val
        
        allocation_pct = {k: round((v / total_value * 100), 2) for k, v in allocation.items()} if total_value > 0 else {}
        
        return {
            'total_value': total_value,
            'allocation_percentage': allocation_pct,
            'holding_count': sum(len(p.holdings.all()) for p in portfolios)
        }

    def _collect_user_profile(self, user: User) -> Dict[str, Any]:
        return {
            'age': user.age,
            'risk_tolerance': user.risk_tolerance,
            'investment_horizon': user.investment_horizon,
            'monthly_income': user.monthly_income,
            'monthly_expenses': user.monthly_expenses
        }

    def _get_market_conditions(self) -> Dict[str, Any]:
        sentiment = self.market_service.get_market_sentiment()
        return {
            'sentiment': sentiment.get('sentiment', 'neutral'),
            'nifty': self.market_service.get_index_data('NIFTY50')
        }
