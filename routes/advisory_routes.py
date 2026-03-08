"""Advisory Routes - Financial advisory endpoints using Gemini AI"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from database.db import db
from database.models import (
    AdvisorySession, FinancialAdvisor, FinancialGoal, 
    Portfolio, Holding, User
)
from services.financial_advisory_service import FinancialAdvisoryService
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

advisory_bp = Blueprint('advisory', __name__, url_prefix='/advisory')

# Initialize service
advisory_service = FinancialAdvisoryService()

@advisory_bp.route('/')
@login_required
def advisory_dashboard():
    """Advisory dashboard - overview of advisory sessions"""
    advisor = advisory_service.get_or_create_advisor(current_user)
    
    sessions = AdvisorySession.query.filter_by(user_id=current_user.id).order_by(
        AdvisorySession.created_at.desc()
    ).limit(10).all()
    
    goals = FinancialGoal.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    session_summary = {
        'total_sessions': len(sessions),
        'active_sessions': sum(1 for s in sessions if s.status == 'active'),
        'portfolio_reviews': sum(1 for s in sessions if s.session_type == 'portfolio_review'),
        'rebalancing_sessions': sum(1 for s in sessions if s.session_type == 'rebalancing'),
    }
    
    return render_template('advisory/dashboard.html',
                         advisor=advisor,
                         sessions=sessions,
                         goals=goals,
                         session_summary=session_summary)

@advisory_bp.route('/portfolio-review', methods=['GET', 'POST'])
@login_required
def portfolio_review():
    """Get comprehensive portfolio review"""
    if request.method == 'GET':
        return render_template('advisory/portfolio_review.html')
    
    try:
        result = advisory_service.conduct_portfolio_review(current_user)
        
        return jsonify({
            'success': True,
            'session_id': result['session_id'],
            'analysis': result['analysis'],
            'portfolio_data': result['portfolio_data']
        })
    except Exception as e:
        logger.error(f"Portfolio review error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@advisory_bp.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    """View detailed advisory session"""
    session = AdvisorySession.query.filter_by(
        id=session_id,
        user_id=current_user.id
    ).first_or_404()
    
    return render_template('advisory/session_detail.html', session=session)

@advisory_bp.route('/rebalancing', methods=['GET', 'POST'])
@login_required
def rebalancing_advice():
    """Get rebalancing recommendations"""
    if request.method == 'GET':
        return render_template('advisory/rebalancing.html')
    
    try:
        result = advisory_service.get_rebalancing_advice(current_user)
        
        return jsonify({
            'success': True,
            'session_id': result['session_id'],
            'analysis': result['analysis']
        })
    except Exception as e:
        logger.error(f"Rebalancing advice error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@advisory_bp.route('/goals')
@login_required
def manage_goals():
    """Manage financial goals"""
    goals = FinancialGoal.query.filter_by(user_id=current_user.id).all()
    
    for goal in goals:
        days_remaining = (goal.target_date - datetime.utcnow()).days
        goal.progress_percentage = min(
            (goal.current_amount_inr / goal.target_amount_inr * 100) if goal.target_amount_inr > 0 else 0,
            100
        )
        goal.days_remaining = max(0, days_remaining)
    
    return render_template('advisory/goals.html', goals=goals)

@advisory_bp.route('/goals/create', methods=['GET', 'POST'])
@login_required
def create_goal():
    """Create new financial goal"""
    if request.method == 'GET':
        return render_template('advisory/create_goal.html')
    
    data = request.get_json()
    
    try:
        goal = FinancialGoal(
            user_id=current_user.id,
            goal_name=data.get('goal_name'),
            goal_category=data.get('goal_category'),
            goal_type=data.get('goal_type', 'financial'),
            target_amount_inr=float(data.get('target_amount', 0)),
            current_amount_inr=float(data.get('current_amount', 0)),
            target_date=datetime.fromisoformat(data.get('target_date')),
            priority=data.get('priority', 'medium')
        )
        
        db.session.add(goal)
        db.session.commit()
        
        # Get AI-powered plan for this goal
        result = advisory_service.get_goal_achievement_plan(current_user, goal.id)
        
        return jsonify({
            'success': True,
            'goal_id': goal.id,
            'session_id': result['session_id'],
            'plan': result['analysis']
        })
    except Exception as e:
        logger.error(f"Create goal error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@advisory_bp.route('/goals/<int:goal_id>/plan')
@login_required
def goal_achievement_plan(goal_id):
    """Get AI-powered plan to achieve goal"""
    goal = FinancialGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    
    # Check if there's an existing plan
    session = AdvisorySession.query.filter_by(
        user_id=current_user.id,
        session_type='goal_setting'
    ).order_by(AdvisorySession.created_at.desc()).first()
    
    if not session:
        # Generate new plan
        result = advisory_service.get_goal_achievement_plan(current_user, goal_id)
        session = AdvisorySession.query.get(result['session_id'])
    
    return render_template('advisory/goal_plan.html', goal=goal, session=session)

@advisory_bp.route('/tax-optimization')
@login_required
def tax_optimization():
    """Tax optimization strategies"""
    try:
        result = advisory_service.get_tax_optimization_advice(current_user)
        session = AdvisorySession.query.get(result['session_id'])
        
        return render_template('advisory/tax_optimization.html', session=session)
    except Exception as e:
        logger.error(f"Tax optimization error: {e}")
        flash(f"Error loading tax optimization: {e}", 'danger')
        return redirect(url_for('advisory.advisory_dashboard'))

@advisory_bp.route('/market-insights')
@login_required
def market_insights():
    """Market insights and implications"""
    try:
        result = advisory_service.get_market_insights(current_user)
        
        return render_template('advisory/market_insights.html',
                             insights=result['market_insights'],
                             market_data=result['market_data'])
    except Exception as e:
        logger.error(f"Market insights error: {e}")
        flash(f"Error loading market insights: {e}", 'danger')
        return redirect(url_for('advisory.advisory_dashboard'))

@advisory_bp.route('/api/sessions')
@login_required
def get_sessions():
    """API endpoint - get user's advisory sessions"""
    sessions = AdvisorySession.query.filter_by(user_id=current_user.id).order_by(
        AdvisorySession.created_at.desc()
    ).limit(20).all()
    
    return jsonify({
        'sessions': [{
            'id': s.id,
            'type': s.session_type,
            'title': s.title,
            'created_at': s.created_at.isoformat(),
            'confidence_score': s.confidence_score,
            'status': s.status
        } for s in sessions]
    })

@advisory_bp.route('/api/session/<int:session_id>/archive', methods=['POST'])
@login_required
def archive_session(session_id):
    """Archive an advisory session"""
    session = AdvisorySession.query.filter_by(
        id=session_id,
        user_id=current_user.id
    ).first_or_404()
    
    session.status = 'archived'
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Session archived'})

@advisory_bp.route('/api/recommendations')
@login_required
def get_recommendations():
    """Get latest recommendations from all sessions"""
    sessions = AdvisorySession.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).order_by(AdvisorySession.created_at.desc()).limit(5).all()
    
    all_recommendations = []
    for session in sessions:
        if session.recommendations:
            all_recommendations.extend(session.recommendations)
    
    return jsonify({
        'recommendations': all_recommendations[:10],
        'total_sessions': len(sessions)
    })

@advisory_bp.route('/api/goals/<int:goal_id>/update-progress', methods=['POST'])
@login_required
def update_goal_progress(goal_id):
    """Update goal progress"""
    goal = FinancialGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    
    data = request.get_json()
    goal.current_amount_inr = float(data.get('current_amount', goal.current_amount_inr))
    goal.progress_percentage = min(
        (goal.current_amount_inr / goal.target_amount_inr * 100) if goal.target_amount_inr > 0 else 0,
        100
    )
    
    if goal.progress_percentage >= 100:
        goal.is_active = False
        goal.target_achieved_date = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'progress': goal.progress_percentage,
        'achieved': goal.is_active == False
    })

@advisory_bp.route('/api/quick-advice', methods=['POST'])
@login_required
def quick_advice():
    """Get quick AI advice on specific question"""
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'Question required'}), 400
    
    try:
        portfolio_data = advisory_service._collect_portfolio_data(current_user)
        user_profile = advisory_service._collect_user_profile(current_user)
        market_data = advisory_service._get_market_conditions()
        
        prompt = f"""You are a financial advisor. Answer this question in context of the user's profile and market:

QUESTION: {question}

USER PORTFOLIO:
- Total Value: ₹{portfolio_data['total_value']:,.0f}
- Returns: {portfolio_data['returns_percentage']:.2f}%
- Allocation: {json.dumps(portfolio_data['allocation_percentage'])}

USER PROFILE:
- Risk: {user_profile['risk_tolerance']}
- Horizon: {user_profile['investment_horizon']}
- Experience: {user_profile['investment_experience']}

MARKET:
- Sentiment: {market_data['sentiment']}
- Volatility: {market_data['volatility']}

Provide a concise, actionable answer (2-3 sentences) followed by specific recommendations if applicable.
Format: {{"answer": "...", "recommendations": [...], "confidence": 0-100}}"""
        
        response = advisory_service._call_gemini_api(prompt)
        
        if not response:
            response = {
                'answer': 'Unable to generate advice at this moment. Please try again later.',
                'recommendations': [],
                'confidence': 0
            }
        
        return jsonify({
            'success': True,
            'advice': response
        })
    except Exception as e:
        logger.error(f"Quick advice error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
