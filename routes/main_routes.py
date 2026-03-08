from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from flask_login import login_required, current_user
from database.db import db
from database.models import Analysis
import logging
from datetime import datetime

from services.market_data_service import MarketDataService
from services.allocation_engine import AllocationEngine
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

# Initialize Services
market_service = MarketDataService()
allocation_engine = AllocationEngine()
gemini_service = GeminiService()

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/insights')
def insights():
    """Market insights page using your MarketDataService methods"""
    try:
        sentiment_data = market_service.get_market_sentiment()
        volatility_data = market_service.get_volatility()
        nifty_data = market_service.get_index_data('NIFTY50')
        
        # Mapping your Service dictionary keys to the template context
        context = {
            'market_sentiment': sentiment_data.get('sentiment', 'neutral'),
            'sentiment_score': sentiment_data.get('sentiment_score', 0),
            'market_volatility': volatility_data.get('volatility_level', 'medium'),
            'volatility_value': volatility_data.get('volatility', 0.018),
            'nifty_change': sentiment_data.get('nifty_change', 0),
            'nifty_value': nifty_data.get('value', 23500),
        }
        return render_template('insights.html', **context)
    except Exception as e:
        logger.error(f"Insights route error: {e}")
        return render_template('insights.html', market_sentiment='neutral')

@main_bp.route('/input-form', methods=['GET', 'POST'])
def input_form():
    goals_list = ["Retirement", "Education", "Home Purchase", "Wedding", "Travel", "Wealth Creation"]
    
    if request.method == 'POST':
        try:
            # 1. Collect inputs
            amount = float(request.form.get('amount', 0))
            risk = request.form.get('risk_tolerance', 'medium')
            horizon = request.form.get('horizon', 'medium')
            
            # Collect selected goals from checkboxes (named 'goals')
            selected_goals = request.form.getlist('goals')
            
            # Save for persistence
            session['last_input'] = request.form.to_dict()
            session['selected_goals'] = selected_goals
            
            # 2. Generate ML Allocation
            allocation_result = allocation_engine.generate_allocation(
                investment_amount=amount,
                risk_tolerance=risk,
                investment_horizon=horizon,
                monthly_income=float(request.form.get('monthly_income', 50000)),
                monthly_expenses=float(request.form.get('monthly_expenses', 30000)),
                age=int(request.form.get('age', 30)),
                investment_experience=int(request.form.get('experience', 1)),
                occupation=int(request.form.get('occupation', 1))
            )

            # 3. Get AI Analysis & Market Data
            market_context = market_service.get_market_sentiment()
            gold_data = market_service.get_gold_price()
            silver_data = market_service.get_silver_price()
            
            # Prepare user profile for Gemini
            user_profile = {
                'age': request.form.get('age', 30), 
                'risk_tolerance': risk,
                'investment_horizon': horizon,
                'investment_amount': amount,
                'financial_goals': ", ".join(selected_goals) if selected_goals else "Generic Growth"
            }

            # Call Gemini for dynamic analysis - use the real dynamic service
            market_data_payload = {
                'sentiment': market_context,
                'gold': gold_data,
                'silver': silver_data
            }
            ai_analysis = gemini_service.get_investment_analysis(
                allocation=allocation_result,
                user_profile=user_profile,
                market_data=market_data_payload
            )

            # XAI Reasoning: justify the recommendation in three explainable pillars
            xai_reasoning = gemini_service.generate_xai_reasoning(
                user_profile=user_profile,
                allocation=allocation_result,
                market_data=market_data_payload
            )

            # 4. Final Package for result.html - Single Source of Truth
            analysis_data = {
                'investment_amount': amount,
                'investment_horizon': horizon,
                'ml_powered': allocation_result.get('ml_powered', False),
                'error': allocation_result.get('error'),
                'market_data': {
                    'gold': gold_data,
                    'silver': silver_data,
                    'sentiment': market_context
                },
                'allocation': allocation_result, # Primary source for all cards and charts
                'ai_analysis': ai_analysis,
                'xai_reasoning': xai_reasoning,  # XAI pillar explanations
                'data_source': 'Proprietary ML + Gemini AI 1.5'
            }

            session['analysis_result'] = analysis_data
            
            # 5. Database Save
            if current_user.is_authenticated:
                from database.models import Analysis
                analysis_rec = Analysis(
                    user_id=current_user.id,
                    investment_amount=amount,
                    risk_tolerance=risk,
                    investment_horizon=horizon,
                    investment_goals=selected_goals,
                    allocation=allocation_result.get('allocation_percentage'),
                    risk_level=allocation_result.get('risk_level'),
                    expected_return_percentage=allocation_result.get('expected_annual_return_percentage'),
                    recommendations=ai_analysis
                )
                db.session.add(analysis_rec)
                db.session.commit()

            return redirect(url_for('main.results', analysis_id=0))
        except Exception as e:
            logger.error(f"Form processing error: {e}", exc_info=True)
            flash(f"Analysis failed: {str(e)}", "danger")
            return redirect(url_for('main.input_form'))

    # GET Request: Get session data or defaults from user profile
    last_input = session.get('last_input', {})
    selected_goals = session.get('selected_goals', [])
    
    # If session is empty but user is logged in, pre-fill from profile
    if not last_input and current_user.is_authenticated:
        last_input = {
            'risk_tolerance': current_user.risk_tolerance or 'medium',
            'horizon': current_user.investment_horizon or 'medium',
            'age': current_user.age or 30,
            'monthly_income': current_user.monthly_income or 50000,
            'monthly_expenses': current_user.monthly_expenses or 30000,
            'experience': current_user.investment_experience or 1
        }

    return render_template('input_form.html', 
                          last_input=last_input, 
                          selected_goals=selected_goals,
                          goals_list=goals_list)

@main_bp.route('/results/<int:analysis_id>')
def results(analysis_id):
    analysis_data = session.get('analysis_result')
    if not analysis_data:
        return redirect(url_for('main.input_form'))
    return render_template('result.html', analysis_data=analysis_data)