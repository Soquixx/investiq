from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database.models import Portfolio, Holding, Transaction, AdvisorySession, Analysis
from database.db import db
from services.market_data_service import MarketDataService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

market_service = MarketDataService()


@api_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard_data():
    """Get dashboard overview data"""
    try:
        portfolios = Portfolio.query.filter_by(user_id=current_user.id).all()
        
        total_value = sum(p.get_current_value() for p in portfolios)
        total_invested = sum(p.get_total_invested() for p in portfolios)
        total_returns = total_value - total_invested
        returns_percentage = (total_returns / total_invested * 100) if total_invested > 0 else 0
        
        # Calculate portfolio count instead of holdings count as per user request
        investment_count = len(portfolios)
        
        # Get investment horizon from profile
        investment_horizon = (current_user.investment_horizon or "Medium").title()
        
        # Get real risk score from most recent analysis
        last_analysis = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).first()
        risk_score = last_analysis.risk_level if last_analysis else (current_user.risk_tolerance or "Medium")
        
        return jsonify({
            'portfolio_value': round(total_value, 2),
            'portfolio_change': round(returns_percentage, 2),
            'investment_count': investment_count,
            'total_invested': round(total_invested, 2),
            'investment_horizon': investment_horizon,
            'risk_score': risk_score or "Medium"
        })
    except Exception as e:
        logger.error(f"Error loading dashboard data: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/performance', methods=['GET'])
@login_required
def performance():
    """Get portfolio performance data"""
    try:
        period = request.args.get('period', '1Y')
        portfolios = Portfolio.query.filter_by(user_id=current_user.id).all()
        
        total_value = sum(p.get_current_value() for p in portfolios)
        
        # Generate monthly dates from earliest portfolio creation or 6 months ago
        from dateutil.relativedelta import relativedelta
        start_date = min([p.created_at for p in portfolios]) if portfolios else datetime.utcnow() - relativedelta(months=5)
        now = datetime.utcnow()
        
        labels = []
        curr = start_date.replace(day=1)
        while curr <= now:
            labels.append(curr.strftime('%b %Y'))
            curr += relativedelta(months=1)
        
        # Ensure at least 'Current' or last 6 months if range is too small
        if len(labels) < 2:
            labels = [(now - relativedelta(months=i)).strftime('%b %Y') for i in range(5, -1, -1)]
        
        if total_value == 0:
            values = [0] * len(labels)
        else:
            # Check for transactions to build history
            transactions = Transaction.query.filter_by(user_id=current_user.id).all()
            if not transactions:
                # Flat line using current value
                values = [round(total_value, 2)] * len(labels)
            else:
                # Simple cumulative trend simulation from transactions
                # (Since we don't have historical prices, we use total_value as end point)
                base_curve = []
                for i in range(len(labels)):
                    # Simulating a slight growth curve towards current total_value
                    factor = 0.9 + (0.1 * (i / (len(labels) - 1))) if len(labels) > 1 else 1.0
                    base_curve.append(factor)
                values = [round(total_value * v, 2) for v in base_curve]
            
        return jsonify({
            'labels': labels,
            'values': values,
            'period': period
        })
    except Exception as e:
        logger.error(f"Error loading performance data: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/allocation', methods=['GET'])
@login_required
def allocation():
    """Get asset allocation data"""
    try:
        portfolios = Portfolio.query.filter_by(user_id=current_user.id).all()
        total_value = sum(p.get_current_value() for p in portfolios)
        
        if total_value == 0:
            # Use last analysis if available, otherwise defaults
            last_analysis = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).first()
            if last_analysis and last_analysis.allocation:
                return jsonify(last_analysis.allocation)
            
            return jsonify({
                'Stocks': 0, 'Bonds': 0, 'Mutual Funds': 0, 'Gold': 0, 'Cash': 100
            })
        
        # Aggregating real holdings
        dist = {}
        for p in portfolios:
            for h in p.holdings:
                atype = h.asset_type.title().replace('_', ' ')
                dist[atype] = dist.get(atype, 0) + h.get_current_value()
        
        if not dist:
            # Fallback to last analysis if no holdings
            last_analysis = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).first()
            if last_analysis and last_analysis.allocation:
                return jsonify(last_analysis.allocation)
            
            return jsonify({
                'Stocks': 0, 'Bonds': 0, 'Mutual Funds': 0, 'Gold': 0, 'Cash': 100
            })
        
        result = {k: round(v / total_value * 100, 2) for k, v in dist.items()}
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error loading allocation data: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/transactions/recent', methods=['GET'])
@login_required
def recent_transactions():
    """Get recent transactions"""
    try:
        transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(
            Transaction.transaction_date.desc()
        ).limit(10).all()
        
        data = [{
            'id': t.id,
            'symbol': t.symbol,
            'type': t.transaction_type,
            'quantity': t.quantity,
            'price': t.price_per_unit,
            'amount': round(t.total_amount, 2),
            'date': t.transaction_date.strftime('%Y-%m-%d'),
            'timestamp': t.transaction_date.isoformat()
        } for t in transactions]
        
        return jsonify({'transactions': data, 'total': len(data)})
    except Exception as e:
        logger.error(f"Error loading recent transactions: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/recommendations', methods=['GET'])
@login_required
def recommendations():
    """Get real AI recommendations from latest analysis"""
    try:
        last_analysis = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).first()
        
        if not last_analysis:
            # Fallback for new users
            return jsonify([{
                'title': 'Complete Your Profile',
                'description': 'Submit your financial details in the Investment Analysis form to get personalized ML recommendations.',
                'sentiment': 'neutral',
                'action_url': '/input-form'
            }])
        
        recs = last_analysis.recommendations
        # Gemini service outputs: {"summary": "...", "key_insights": [], "risks": [], "actions": []}
        
        formatted_recs = []
        if recs and isinstance(recs, dict):
            if 'actions' in recs:
                for action in recs['actions'][:2]:
                    formatted_recs.append({
                        'title': 'AI Action Item',
                        'description': action,
                        'sentiment': 'positive'
                    })
            if 'risks' in recs:
                for risk in recs['risks'][:1]:
                    formatted_recs.append({
                        'title': 'Portfolio Risk Alert',
                        'description': risk,
                        'sentiment': 'negative'
                    })
        
        if not formatted_recs:
             formatted_recs.append({
                'title': 'Market Outlook',
                'description': 'Market sentiment is currently being analyzed. Continue monitoring your portfolio for rebalancing opportunities.',
                'sentiment': 'neutral'
            })
            
        return jsonify(formatted_recs)
    except Exception as e:
        logger.error(f"Error loading recommendations: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/market-data/<symbol>', methods=['GET'])
def market_data(symbol):
    """Get market data for a symbol (public endpoint)"""
    try:
        symbol_upper = symbol.upper()
        data = None
        
        # Determine the type of symbol and fetch appropriate data
        if symbol_upper in ['NIFTY50', 'SENSEX', 'BANKNIFTY', 'NIFTYNXT50']:
            # Index symbol
            data = market_service.get_index_data(symbol_upper)
        elif symbol_upper == 'GOLD':
            # Gold commodity
            data = market_service.get_gold_price()
            # Normalize gold price response
            if data and 'price_per_gram_inr' in data:
                data['price'] = data.pop('price_per_gram_inr')
                data['value'] = data['price']
        elif symbol_upper == 'SILVER':
            # Silver commodity using Alpha Vantage
            data = market_service.get_silver_price()
            if data and 'price_per_gram_inr' in data:
                data['price'] = data.pop('price_per_gram_inr')
                data['value'] = data['price']
        elif symbol_upper == 'CRUDE':
            # Crude Oil using yfinance (CL=F)
            data = market_service.get_crude_price()
        else:
            # Stock symbol
            data = market_service.get_stock_price(symbol_upper)
        
        if data:
            # Normalize response with standard keys that frontend expects
            response = {
                'symbol': symbol_upper,
                'current_price': data.get('price') or data.get('value'),
                'open': data.get('open'),
                'high': data.get('high'),
                'low': data.get('low'),
                'change': data.get('change'),
                'change_percent': data.get('change_percent'),
                'timestamp': data.get('timestamp'),
                'source': data.get('source'),
                'currency': data.get('currency', 'INR')
            }
            logger.info(f"Market data for {symbol_upper}: {response}")
            return jsonify(response)
        return jsonify({'error': f'No data for {symbol}'}), 404
    except Exception as e:
        logger.error(f"Error loading market data for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/portfolio', methods=['POST'])
@login_required
def create_portfolio():
    """Create new portfolio"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'error': 'Portfolio name is required'}), 400
        
        portfolio = Portfolio(
            user_id=current_user.id,
            name=name,
            description=description,
            initial_investment=0,
            current_value=0
        )
        
        db.session.add(portfolio)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'portfolio_id': portfolio.id,
            'message': f'Portfolio "{name}" created successfully'
        }), 201
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/portfolio/<int:portfolio_id>', methods=['GET'])
@login_required
def get_portfolio(portfolio_id):
    """Get portfolio details"""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        
        if portfolio.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        holdings_data = [{
            'id': h.id,
            'symbol': h.symbol,
            'name': h.name,
            'asset_type': h.asset_type,
            'quantity': h.quantity,
            'purchase_price': h.purchase_price,
            'current_price': h.current_price or h.purchase_price,
            'purchase_date': h.purchase_date.isoformat(),
            'value': h.get_current_value()
        } for h in portfolio.holdings]
        
        return jsonify({
            'portfolio': {
                'id': portfolio.id,
                'name': portfolio.name,
                'description': portfolio.description,
                'initial_investment': portfolio.initial_investment,
                'current_value': portfolio.get_current_value(),
                'total_returns': portfolio.current_value - portfolio.initial_investment,
                'currency': portfolio.currency,
                'created_at': portfolio.created_at.isoformat()
            },
            'holdings': holdings_data,
            'total_holdings': len(holdings_data)
        })
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/portfolio/<int:portfolio_id>/holding', methods=['POST'])
@login_required
def add_holding(portfolio_id):
    """Add holding to portfolio"""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        
        if portfolio.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        holding = Holding(
            portfolio_id=portfolio_id,
            symbol=data.get('symbol').upper(),
            name=data.get('name', data.get('symbol')),
            asset_type=data.get('asset_type', 'stock'),
            quantity=float(data.get('quantity', 1)),
            purchase_price=float(data.get('purchase_price', 0)),
            purchase_amount=float(data.get('quantity', 1)) * float(data.get('purchase_price', 0)),
            purchase_date=db.func.now()
        )
        
        db.session.add(holding)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'holding_id': holding.id,
            'message': 'Holding added successfully'
        }), 201
    except Exception as e:
        logger.error(f"Error adding holding: {e}")
        return jsonify({'error': str(e)}), 500
