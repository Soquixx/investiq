from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from database.db import db
from database.models import Portfolio, Holding, Transaction, AdvisorySession
from datetime import datetime, timedelta
from services.market_data_service import MarketDataService
from services.financial_advisory_service import FinancialAdvisoryService
import json
import logging

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)

# Initialize services
market_service = MarketDataService()
advisory_service = FinancialAdvisoryService()

@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard home"""
    portfolios = Portfolio.query.filter_by(user_id=current_user.id).all()
    
    # Calculate totals in INR
    total_value = sum(p.get_current_value() for p in portfolios)
    total_invested = sum(p.get_total_invested() for p in portfolios)
    total_returns = total_value - total_invested
    returns_percentage = (total_returns / total_invested * 100) if total_invested > 0 else 0
    
    investment_count = sum(len(p.holdings.all()) for p in portfolios)
    
    # Mock recent transactions
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(
        Transaction.transaction_date.desc()
    ).limit(5).all()
    
    recent_transactions = [{
        'asset': t.symbol,
        'type': t.transaction_type,
        'date': t.transaction_date.strftime('%d-%m-%Y'),
        'amount': f'₹{t.total_amount:,.2f}'
    } for t in transactions]
    
    # Get market insights with defensive fallback
    market_sentiment_raw = market_service.get_market_sentiment()
    market_sentiment = market_sentiment_raw if isinstance(market_sentiment_raw, dict) else {
        'sentiment': 'neutral', 'sentiment_score': 0, 'nifty_change': 0
    }
    
    nifty_raw = market_service.get_index_data('NIFTY50')
    nifty = nifty_raw if isinstance(nifty_raw, dict) else {
        'value': 23500, 'change_percent': 0
    }
    
    # Get latest analysis for risk score and allocation fallback
    from database.models import Analysis
    last_analysis = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).first()
    risk_score = last_analysis.risk_level if last_analysis else (current_user.risk_tolerance or "Medium")
    
    latest_session = AdvisorySession.query.filter_by(user_id=current_user.id).order_by(
        AdvisorySession.created_at.desc()
    ).first()
    
    # AI recommendations based on current market
    ai_recommendations = [
        {
            'title': f'Market Sentiment: {market_sentiment.get("sentiment", "neutral").title()}',
            'description': f'Current market sentiment score: {market_sentiment.get("sentiment_score", 0):.2f}. NIFTY50 at Rs.{nifty.get("value", 0):,.0f}',
            'sentiment': 'positive' if market_sentiment.get('sentiment') == 'bullish' else 'negative' if market_sentiment.get('sentiment') == 'bearish' else 'neutral'
        },
        {
            'title': 'Diversification Check',
            'description': 'Review your portfolio asset allocation quarterly to maintain risk balance.',
            'sentiment': 'neutral'
        }
    ]
    
    # Calculate portfolio count as per user request
    investment_count = len(portfolios)
    
    # Investment horizon from profile
    investment_horizon = (current_user.investment_horizon or "Medium").title()

    return render_template('dashboard.html',
        portfolio_value=f'₹{total_value:,.2f}',
        portfolio_change=returns_percentage,
        investment_count=investment_count,
        investment_horizon=investment_horizon,
        risk_score=risk_score,
        recent_transactions=recent_transactions,
        ai_recommendations=ai_recommendations,
        market_sentiment=market_sentiment.get('sentiment', 'neutral'),
        nifty_value=f"₹{nifty.get('value', 0):,.2f}",
        latest_advisory_session=latest_session
    )

@dashboard_bp.route('/portfolio')
@login_required
def portfolio():
    """Portfolio management"""
    portfolios = Portfolio.query.filter_by(user_id=current_user.id).all()
    return render_template('portfolio.html', portfolios=portfolios)

@dashboard_bp.route('/portfolio/create', methods=['GET', 'POST'])
@login_required
def create_portfolio():
    """Create a new portfolio"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        initial_investment = request.form.get('initial_investment', 0)
        
        try:
            initial_investment = float(initial_investment)
        except (ValueError, TypeError):
            initial_investment = 0.0
            
        new_portfolio = Portfolio(
            user_id=current_user.id,
            name=name,
            description=description,
            initial_investment=initial_investment,
            current_value=initial_investment,
            total_returns=0.0,
            returns_percentage=0.0
        )
        
        db.session.add(new_portfolio)
        db.session.commit()
        
        return redirect(url_for('dashboard.portfolio'))
        
    return render_template('create_portfolio.html')

@dashboard_bp.route('/portfolio/<int:portfolio_id>/delete', methods=['POST'])
@login_required
def delete_portfolio(portfolio_id):
    """Delete a portfolio"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    
    if portfolio.user_id != current_user.id:
        return {'error': 'Unauthorized'}, 403
        
    db.session.delete(portfolio)
    db.session.commit()
    
    return redirect(url_for('dashboard.portfolio'))

@dashboard_bp.route('/portfolio/<int:portfolio_id>')
@login_required
def portfolio_detail(portfolio_id):
    """Portfolio detail view"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    
    if portfolio.user_id != current_user.id:
        return {'error': 'Unauthorized'}, 403
    
    holdings = portfolio.holdings.all()
    
    return render_template('portfolio_detail.html',
        portfolio=portfolio,
        holdings=holdings
    )

@dashboard_bp.route('/api/portfolio/<int:portfolio_id>/data')
@login_required
def portfolio_data(portfolio_id):
    """Get portfolio data for charts"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    
    if portfolio.user_id != current_user.id:
        return {'error': 'Unauthorized'}, 403
    
    holdings = portfolio.holdings.all()
    
    data = {
        'portfolio': {
            'id': portfolio.id,
            'name': portfolio.name,
            'total_value': portfolio.get_current_value(),
            'currency': portfolio.currency
        },
        'holdings': [{
            'symbol': h.symbol,
            'quantity': h.quantity,
            'purchase_price': h.purchase_price,
            'current_price': h.current_price or h.purchase_price,
            'value': (h.current_price or h.purchase_price) * h.quantity
        } for h in holdings]
    }
    
    return jsonify(data)

@dashboard_bp.route('/transactions')
@login_required
def transactions():
    """View all transactions"""
    page = request.args.get('page', 1, type=int)
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(
        Transaction.transaction_date.desc()
    ).paginate(page=page, per_page=20)
    
    return render_template('transactions.html', transactions=transactions)

@dashboard_bp.route('/profile')
@login_required
def profile():
    """User profile"""
    return render_template('profile.html', user=current_user)

@dashboard_bp.route('/settings')
@login_required
def settings():
    """User settings"""
    return render_template('settings.html')

@dashboard_bp.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    data = request.get_json() or request.form
    
    current_user.first_name = data.get('first_name', current_user.first_name)
    current_user.last_name = data.get('last_name', current_user.last_name)
    current_user.risk_tolerance = data.get('risk_tolerance', current_user.risk_tolerance)
    current_user.investment_horizon = data.get('investment_horizon', current_user.investment_horizon)
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Profile updated'})

# Dynamic Asset Allocation API Endpoints

@dashboard_bp.route('/api/dynamic-allocation', methods=['POST'])
@login_required
def get_dynamic_allocation():
    """Get dynamic asset allocation recommendation"""
    try:
        from services.allocation_engine import AllocationEngine
        allocation_engine = AllocationEngine()

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Map UI risk/horizon to engine expectations
        risk_tolerance = data.get('risk_tolerance', current_user.risk_tolerance or 'medium')
        investment_horizon = data.get('investment_horizon', current_user.investment_horizon or 'medium')
        
        result = allocation_engine.generate_allocation(
            investment_amount=float(data.get('portfolio_value', 100000)),
            risk_tolerance=risk_tolerance,
            investment_horizon=investment_horizon,
            monthly_income=float(data.get('income', current_user.monthly_income or 50000)),
            monthly_expenses=float(data.get('expenses', 30000)),
            age=int(data.get('age', current_user.age or 35))
        )

        return jsonify({
            'allocation': result.get('allocation_percentage'),
            'metrics': {
                'expected_return': result.get('expected_annual_return_percentage'),
                'risk_level': result.get('investor_type')
            },
            'ml_powered': result.get('ml_powered', False),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in dynamic allocation API: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@dashboard_bp.route('/api/rebalance-recommendations', methods=['POST'])
@login_required
def get_rebalance_recommendations():
    """Get portfolio rebalancing recommendations"""
    try:
        # Reusing AllocationEngine to simulate rebalance logic as the previous service was missing
        from services.allocation_engine import AllocationEngine
        allocation_engine = AllocationEngine()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        current_allocation = data.get('current_allocation', {})
        portfolio_value = data.get('portfolio_value', 100000)
        
        # Determine target based on profile
        target = allocation_engine._rule_based_allocation(
            current_user.risk_tolerance or 'medium', 
            portfolio_value
        )

        # Simple rebalance logic
        trades = []
        target_pct = target.get('allocation_percentage', {})
        for asset, t_pct in target_pct.items():
            c_pct = current_allocation.get(asset, 0)
            diff = t_pct - c_pct
            if abs(diff) > 5:
                trades.append({
                    'asset': asset,
                    'action': 'Buy' if diff > 0 else 'Sell',
                    'percentage': abs(diff),
                    'amount': (abs(diff) / 100) * portfolio_value
                })

        return jsonify({
            'current_allocation': current_allocation,
            'target_allocation': target_pct,
            'trades_required': trades,
            'expected_improvement': 2.5
        })

    except Exception as e:
        logger.error(f"Error in rebalance recommendations API: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@dashboard_bp.route('/api/allocation-diagnostics', methods=['GET'])
@login_required
def get_allocation_diagnostics():
    """Get allocation system diagnostics"""
    try:
        from services.allocation_engine import AllocationEngine
        from services.ml_engine import MLEngine
        
        ae = AllocationEngine()
        me = MLEngine()
        
        return jsonify({
            'ml_engine_ready': me.investor_classifier is not None,
            'allocation_engine_ready': True,
            'models_loaded': {
                'classifier': me.investor_classifier is not None,
                'allocator': me.asset_allocator is not None,
                'return_predictor': me.return_predictor is not None
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in allocation diagnostics API: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@dashboard_bp.route('/api/market-data/<symbol>', methods=['GET'])
@login_required
def get_market_data(symbol):
    """Get real-time market data for a symbol"""
    try:
        from services.market_data_service import MarketDataService

        market_service = MarketDataService()
        data = market_service.get_market_data(symbol.upper())

        if data:
            return jsonify(data)
        else:
            return jsonify({'error': f'No data available for {symbol}'}), 404

    except Exception as e:
        logger.error(f"Error fetching market data for {symbol}: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

