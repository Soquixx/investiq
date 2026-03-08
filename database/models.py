from database.db import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

class User(UserMixin, db.Model):
    """User model - Enhanced for Indian financial context"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    
    # Profile info - Indian Financial Context
    age = db.Column(db.Integer)
    risk_tolerance = db.Column(db.String(20), default='medium')  # low, medium, high
    investment_horizon = db.Column(db.String(20))  # short (<3 years), medium (3-10 years), long (>10 years)
    monthly_income = db.Column(db.Float)  # In INR
    monthly_expenses = db.Column(db.Float)  # In INR
    annual_savings = db.Column(db.Float)  # In INR
    
    # Financial goals (JSON for flexibility)
    financial_goals = db.Column(db.JSON, default={})  # e.g., {"wealth_creation": True, "retirement": True}
    
    # Investment experience
    investment_experience = db.Column(db.String(20))  # beginner, intermediate, expert
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    portfolios = db.relationship('Portfolio', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    analyses = db.relationship('Analysis', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_total_portfolio_value(self) -> float:
        """Calculate total portfolio value in INR"""
        return sum(p.get_current_value() for p in self.portfolios if p.is_active)
    
    def get_total_invested_amount(self) -> float:
        """Calculate total invested amount in INR"""
        return sum(p.initial_investment for p in self.portfolios if p.is_active)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Portfolio(db.Model):
    """Portfolio model - Enhanced for Indian assets"""
    __tablename__ = 'portfolios'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    
    # Value tracking in INR
    initial_investment = db.Column(db.Float, default=0.0)  # INR
    current_value = db.Column(db.Float, default=0.0)  # INR
    
    # Asset mix (stored as JSON for flexibility)
    asset_allocation = db.Column(db.JSON, default={})
    
    # Portfolio metadata
    is_active = db.Column(db.Boolean, default=True)
    currency = db.Column(db.String(3), default='INR')
    
    # Performance tracking
    total_returns = db.Column(db.Float, default=0.0)  # In INR
    returns_percentage = db.Column(db.Float, default=0.0)  # In percentage
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    holdings = db.relationship('Holding', backref='portfolio', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_current_value(self) -> float:
        """Calculate current portfolio value in INR"""
        holdings = self.holdings.all()
        if not holdings:
            return self.initial_investment
        return sum(h.get_current_value() for h in holdings)
    
    @property
    def total_value(self) -> float:
        """Property to get current portfolio value"""
        return self.get_current_value()
    
    def get_total_invested(self) -> float:
        """Calculate total invested amount in INR from holdings, fallbacks to initial_investment if no holdings"""
        holdings = self.holdings.all()
        if not holdings:
            return self.initial_investment
        return sum(h.purchase_price * h.quantity for h in holdings)
    
    def update_current_value(self):
        """Update portfolio current value"""
        self.current_value = self.get_current_value()
        total_invested = self.get_total_invested()
        self.total_returns = self.current_value - total_invested
        if total_invested > 0:
            self.returns_percentage = (self.total_returns / total_invested) * 100
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<Portfolio {self.name}>'

class Holding(db.Model):
    """Holding model - Stocks, Mutual Funds, ETFs, etc."""
    __tablename__ = 'holdings'
    
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False, index=True)
    
    # Asset identification
    symbol = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(255))
    asset_type = db.Column(db.String(50), nullable=False)  # stock, mutual_fund, etf, gold, fixed_deposit, bond
    
    # Quantity and pricing
    quantity = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)  # INR per unit
    current_price = db.Column(db.Float)  # INR per unit
    
    # Investment details
    purchase_date = db.Column(db.DateTime, nullable=False)
    purchase_amount = db.Column(db.Float)  # Total purchased amount in INR
    
    # For specific asset types
    isin = db.Column(db.String(20))  # For mutual funds and bonds
    nav = db.Column(db.Float)  # Net Asset Value for mutual funds
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_current_value(self) -> float:
        """Get current value of this holding in INR"""
        if self.current_price:
            return self.quantity * self.current_price
        return self.quantity * self.purchase_price

    def get_returns(self) -> dict:
        """Calculate returns for this holding"""
        current_value = self.get_current_value()
        invested_amount = self.purchase_amount or (self.quantity * self.purchase_price)
        returns_amount = current_value - invested_amount
        returns_percentage = (returns_amount / invested_amount * 100) if invested_amount > 0 else 0
        
        return {
            "amount": returns_amount,
            "percentage": returns_percentage,
            "current_value": current_value,
            "invested_amount": invested_amount
        }
    
    def __repr__(self):
        return f'<Holding {self.symbol}>'

class Transaction(db.Model):
    """Transaction model"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), index=True)
    
    # Transaction details
    symbol = db.Column(db.String(20), nullable=False, index=True)
    asset_type = db.Column(db.String(50))  # stock, mutual_fund, etf, gold, etc.
    transaction_type = db.Column(db.String(20), nullable=False)  # buy, sell, dividend, interest, etc.
    
    # Quantity and pricing
    quantity = db.Column(db.Float)
    price_per_unit = db.Column(db.Float)  # INR per unit
    total_amount = db.Column(db.Float, nullable=False)  # Total in INR
    
    # Charges and taxes
    brokerage = db.Column(db.Float, default=0.0)  # INR
    taxes = db.Column(db.Float, default=0.0)  # INR
    
    # Timestamps
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Analysis(db.Model):
    """Analysis model - AI results"""
    __tablename__ = 'analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Analysis parameters
    investment_amount = db.Column(db.Float, nullable=False)  # INR
    risk_tolerance = db.Column(db.String(20))
    investment_horizon = db.Column(db.String(20))
    investment_goals = db.Column(db.JSON)
    
    # Analysis results
    recommendations = db.Column(db.JSON)  # Store recommendations as JSON
    overall_score = db.Column(db.Float)  # 0-100
    expected_return_percentage = db.Column(db.Float)  # Annual expected return %
    risk_level = db.Column(db.String(20))
    volatility = db.Column(db.Float)
    sharpe_ratio = db.Column(db.Float)
    
    # Asset allocation breakdown
    allocation = db.Column(db.JSON, default={})  # {stocks: 50, bonds: 30, ...}
    
    # Market data source
    market_data_source = db.Column(db.String(50))  # finnhub, demo, etc.
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Recommendation(db.Model):
    """Recommendation model - Individual recommendations from analysis"""
    __tablename__ = 'recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analyses.id'), nullable=False, index=True)
    
    # Asset details
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(255))
    asset_type = db.Column(db.String(50))
    
    # Recommendation details
    action = db.Column(db.String(20))  # buy, hold, sell
    allocation_percentage = db.Column(db.Float)  # % of portfolio
    allocation_amount = db.Column(db.Float)  # Amount in INR
    confidence_score = db.Column(db.Float)  # 0-100
    
    # Explanation
    reasoning = db.Column(db.Text)
    risk_level = db.Column(db.String(20))
    expected_annual_return = db.Column(db.Float)  # %
    
    # Metadata
    source = db.Column(db.String(50))  # AI, rule-based, etc.
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FinancialAdvisor(db.Model):
    """Financial Advisor model - AI-powered advisory sessions and recommendations"""
    __tablename__ = 'financial_advisors'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Advisor metadata
    name = db.Column(db.String(120), default='Gemini Financial Advisor')
    specialization = db.Column(db.String(100), default='Portfolio Management')
    
    # Advisor credentials and capabilities
    certification = db.Column(db.JSON, default={})  # {level: "expert", domains: [...]}
    analysis_count = db.Column(db.Integer, default=0)
    
    # Advisor preferences
    analysis_frequency = db.Column(db.String(20))  # weekly, monthly, quarterly
    preferred_contact = db.Column(db.String(50))  # email, in-app, sms
    
    # Status and activity
    is_active = db.Column(db.Boolean, default=True)
    last_analysis_date = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    advisory_sessions = db.relationship('AdvisorySession', backref='advisor', lazy='dynamic', cascade='all, delete-orphan')

class AdvisorySession(db.Model):
    """Advisory Session model - Updated for Gemini 1.5"""
    __tablename__ = 'advisory_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey('financial_advisors.id'), nullable=False, index=True)
    
    # Session context
    session_type = db.Column(db.String(50), nullable=False)  # portfolio_review, rebalancing, goal_setting, emergency_planning, tax_optimization
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # User context at time of advisory
    portfolio_value_inr = db.Column(db.Float)  # INR
    user_risk_profile = db.Column(db.String(20))  # low, medium, high
    time_horizon = db.Column(db.String(20))  # short, medium, long
    
    # Advisory content
    ai_prompt = db.Column(db.Text)  # The prompt sent to Gemini
    advisor_response = db.Column(db.JSON)  # Structured response from Gemini
    
    # Analysis and recommendations
    key_findings = db.Column(db.JSON)  # List of key findings
    recommendations = db.Column(db.JSON)  # List of specific recommendations
    action_items = db.Column(db.JSON)  # List of actionable items for user
    
    # Metrics
    confidence_score = db.Column(db.Float)  # 0-100
    risk_score = db.Column(db.Float)  # 0-100
    opportunity_score = db.Column(db.Float)  # 0-100
    
    # Follow-up
    follow_up_date = db.Column(db.DateTime)
    follow_up_reminder_sent = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='active')  # active, archived, completed
    
    # AI Model information
    ai_model = db.Column(db.String(50), default='gemini-1.5-flash') 
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FinancialGoal(db.Model):
    """Financial Goal model"""
    __tablename__ = 'financial_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Goal definition
    goal_name = db.Column(db.String(120), nullable=False)
    goal_category = db.Column(db.String(50), nullable=False)  # retirement, education, wedding, home, vacation, etc.
    goal_type = db.Column(db.String(20), nullable=False, default='financial') # financial or milestone
    
    # Goal parameters
    target_amount_inr = db.Column(db.Float, nullable=False)  # In INR
    current_amount_inr = db.Column(db.Float, default=0.0)  # Amount saved so far
    target_date = db.Column(db.DateTime, nullable=False)  # When goal needs to be achieved
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    
    # Strategy and tracking
    allocation_strategy = db.Column(db.JSON, default={})  # Suggested allocation
    monthly_investment_required = db.Column(db.Float, default=0.0)  # INR to invest monthly
    expected_return_rate = db.Column(db.Float, default=0.0)  # Expected annual return %
    
    # Status
    progress_percentage = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    target_achieved_date = db.Column(db.DateTime)