import os
import logging
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session config - ensure browser session only
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_SECURE = False  # False for development
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    
    # JWT config
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///investiq.db'
    
    # Flask settings
    DEBUG = False
    PORT = int(os.environ.get('PORT', 5000))
    
    # Pagination
    ITEMS_PER_PAGE = 10
    
    # File uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    
    # Logging
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'investiq.log')
    
    # Indian Financial Settings
    CURRENCY = 'INR'
    CURRENCY_SYMBOL = '₹'
    DATE_FORMAT = '%d-%m-%Y'
    
    # API Keys 
    FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')
    
    # Indian Asset Symbols
    INDIAN_STOCKS = [
        'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN',
        'AIRTEL', 'WIPRO', 'MARUTI', 'LT', 'ADANIENT', 'BAJAJFINSV'
    ]
    
    MUTUAL_FUNDS = [
        'NIFTYNXT50', 'NIFTYLOWVOL50', 'NIFTY50VALUE', 'NIFTY50GROWTH'
    ]
    
    ETF_SYMBOLS = [
        'ICICINIFTY50ETF', 'NIFTYBEES', 'GOLDBEES', 'SILVBEES'
    ]


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    DEBUG = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
