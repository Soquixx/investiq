"""Market Data Service - Production-grade real Indian market data"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

class MarketDataService:
    """Real-time Indian market data from NSE/BSE using multiple sources"""
    
    # Indian stocks (NSE symbols)
    INDIAN_STOCKS = {
        'RELIANCE': 'Reliance Industries Limited',
        'TCS': 'Tata Consultancy Services',
        'INFY': 'Infosys Limited',
        'HDFCBANK': 'HDFC Bank Limited',
        'ICICIBANK': 'ICICI Bank Limited',
        'SBIN': 'State Bank of India',
        'WIPRO': 'Wipro Limited',
        'MARUTI': 'Maruti Suzuki India',
        'LT': 'Larsen & Toubro Limited',
        'ITC': 'ITC Limited',
        'SUNPHARMA': 'Sun Pharmaceutical Industries',
        'TATAMOTORS': 'Tata Motors Limited',
        'HINDUNILVR': 'Hindustan Unilever Limited',
        'NESTLEIND': 'Nestle India Limited',
        'BAJAJFINSV': 'Bajaj Finserv Limited'
    }
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes cache for market data
        self.timeout = 15  # API timeout
        self.alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY") or os.getenv("ALPHAKEY")
        if not self.alpha_key:
            logger.warning("Alpha Vantage API Key missing. Commodity prices may fail.")
        logger.info("MarketDataService initialized with Alpha Vantage and yfinance")
    
    def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """Get live stock price using yfinance"""
        cache_key = f"stock_{symbol}"
        
        default_data = {
            'symbol': symbol,
            'price': 0.0,
            'open': 0.0,
            'high': 0.0,
            'low': 0.0,
            'change': 0.0,
            'change_percent': 0.0,
            'timestamp': datetime.now().isoformat(),
            'source': 'fallback',
            'currency': 'INR'
        }

        if self._is_cached(cache_key):
            value, _ = self.cache[cache_key]
            return value
        
        try:
            import yfinance as yf
            
            # Ensure NSE format
            ticker_symbol = f"{symbol}.NS" if not symbol.endswith(('.NS', '.BO')) else symbol
            ticker = yf.Ticker(ticker_symbol)
            
            # Try fast_info
            try:
                fast_info = ticker.fast_info
                price = float(fast_info.last_price) if hasattr(fast_info, 'last_price') and fast_info.last_price else None
                open_p = float(fast_info.open) if hasattr(fast_info, 'open') and fast_info.open else None
                high = float(fast_info.day_high) if hasattr(fast_info, 'day_high') and fast_info.day_high else None
                low = float(fast_info.day_low) if hasattr(fast_info, 'day_low') and fast_info.day_low else None
            except Exception:
                price = None

            # Fallback to history if fast_info has no data
            if not price:
                # Use 5d to ensure we get data even outside market hours / weekends
                hist = ticker.history(period='5d', auto_adjust=True)
                if hist.empty:
                    logger.warning(f"No history data for {ticker_symbol}")
                    return default_data
                last_row = hist.iloc[-1]
                price = float(last_row['Close'])
                open_p = float(last_row['Open'])
                high = float(last_row['High'])
                low = float(last_row['Low'])
            else:
                open_p = open_p or price
                high = high or price
                low = low or price

            price_data = {
                'symbol': symbol,
                'price': round(price, 2),
                'open': round(open_p, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'change': round(price - open_p, 2),
                'change_percent': round(((price - open_p) / open_p * 100) if open_p > 0 else 0, 2),
                'timestamp': datetime.now().isoformat(),
                'source': 'yfinance-nse',
                'currency': 'INR'
            }
            
            self._cache_set(cache_key, price_data)
            logger.info(f"Stock price fetched for {symbol}: {price:.2f}")
            return price_data
            
        except Exception as e:
            logger.error(f"yfinance failed for {symbol}: {e}")
            return default_data
    
    def get_index_data(self, index: str) -> Dict[str, Any]:
        """Get NSE/BSE index data"""
        cache_key = f"index_{index}"
        
        default_data = {
            'symbol': index,
            'symbol': index,
            'value': 23500.0 if index == 'NIFTY50' else 77000.0,
            'open': 23500.0 if index == 'NIFTY50' else 77000.0,
            'change': 0.0,
            'change_percent': 0.0,
            'timestamp': datetime.now().isoformat(),
            'source': 'fallback',
            'currency': 'INR'
        }

        if self._is_cached(cache_key):
            value, _ = self.cache[cache_key]
            return value
        
        try:
            import yfinance as yf
            
            ticker_map = {
                'NIFTY50': '^NSEI',
                'SENSEX': '^BSESN',
                'NIFTYNXT50': '^NIFTYIT',
                'BANKNIFTY': '^NSEBANK',
                'NIFTYMIDCAP': '^CNXMID'
            }
            
            ticker_sym = ticker_map.get(index)
            if not ticker_sym:
                return default_data
                
            ticker = yf.Ticker(ticker_sym)
            # Use 5d to ensure data is available even outside market hours / weekends
            hist = ticker.history(period='5d', auto_adjust=True)
            
            if hist.empty:
                logger.error(f"yfinance returned no history for index {index} ({ticker_sym})")
                return default_data
            
            last_row = hist.iloc[-1]
            price = float(last_row['Close'])
            open_p = float(last_row['Open'])
            prev_close = float(hist.iloc[-2]['Close']) if len(hist) >= 2 else open_p
            
            index_data = {
                'symbol': index,
                'value': round(price, 2),
                'open': round(open_p, 2),
                'prev_close': round(prev_close, 2),
                'change': round(price - prev_close, 2),
                'change_percent': round(((price - prev_close) / prev_close * 100) if prev_close > 0 else 0, 2),
                'timestamp': datetime.now().isoformat(),
                'source': 'yfinance',
                'currency': 'INR'
            }
            
            self._cache_set(cache_key, index_data)
            logger.info(f"Index {index} fetched: {price:.2f} ({index_data['change_percent']:+.2f}%)")
            return index_data
            
        except Exception as e:
            logger.error(f"Failed to get index {index}: {e}")
            return default_data
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """Get market sentiment from index performance"""
        cache_key = 'market_sentiment'
        
        if self._is_cached(cache_key):
            value, _ = self.cache[cache_key]
            return value
        
        try:
            nifty = self.get_index_data('NIFTY50')
            sensex = self.get_index_data('SENSEX')
            
            # Ensure we have valid dictionaries
            if not isinstance(nifty, dict):
                nifty = {'change_percent': 0}
            if not isinstance(sensex, dict):
                sensex = {'change_percent': 0}
            
            # Calculate aggregate sentiment
            changes = []
            nifty_change = nifty.get('change_percent', 0)
            sensex_change = sensex.get('change_percent', 0)
            
            if isinstance(nifty_change, (int, float)):
                changes.append(nifty_change)
            if isinstance(sensex_change, (int, float)):
                changes.append(sensex_change)
            
            avg_change = sum(changes) / len(changes) if changes else 0
            
            sentiment = 'bullish' if avg_change > 0.5 else 'bearish' if avg_change < -0.5 else 'neutral'
            
            data = {
                'sentiment': sentiment,
                'sentiment_score': float(avg_change),
                'nifty_change': float(nifty_change),
                'sensex_change': float(sensex_change),
                'timestamp': datetime.now().isoformat(),
                'source': 'market_indices',
                'currency': 'INR'
            }
            
            self._cache_set(cache_key, data)
            return data
            
        except Exception as e:
            logger.error(f"Sentiment calculation error: {e}")
            return {
                'sentiment': 'neutral',
                'sentiment_score': 0,
                'timestamp': datetime.now().isoformat(),
                'source': 'fallback'
            }
    
    def get_volatility(self) -> Dict[str, Any]:
        """Get market volatility estimate"""
        cache_key = 'market_volatility'
        
        if self._is_cached(cache_key):
            value, _ = self.cache[cache_key]
            return value
        
        try:
            import yfinance as yf
            import pandas as pd
            
            # Get 5-day volatility from top 3 stocks
            stocks = ['RELIANCE', 'TCS', 'HDFCBANK']
            volatilities = []
            
            for stock in stocks:
                try:
                    ticker = f"{stock}.NS"
                    ticker_obj = yf.Ticker(ticker)
                    data = ticker_obj.history(period='5d', auto_adjust=True)
                    
                    if isinstance(data, pd.DataFrame) and len(data) > 0:
                        close_series = data['Close']
                        # Handle multi-level columns if present
                        if hasattr(close_series, 'columns'):
                            close_series = close_series.iloc[:, 0]
                        returns = close_series.pct_change().dropna()
                        vol = float(returns.std())
                        if isinstance(vol, (int, float)) and not pd.isna(vol):
                            volatilities.append(vol)
                except Exception as ve:
                    logger.debug(f"Volatility fetch failed for {stock}: {ve}")
                    pass
            
            avg_vol = sum(volatilities) / len(volatilities) if volatilities else 0.015
            vol_level = 'low' if avg_vol < 0.01 else 'medium' if avg_vol < 0.025 else 'high'
            
            data = {
                'volatility': float(avg_vol),
                'volatility_level': vol_level,
                'timestamp': datetime.now().isoformat(),
                'source': 'calculated',
                'currency': 'INR'
            }
            
            self._cache_set(cache_key, data)
            return data
            
        except Exception as e:
            logger.error(f"Volatility error: {e}")
            return {
                'volatility': 0.018,
                'volatility_level': 'medium',
                'timestamp': datetime.now().isoformat(),
                'source': 'fallback'
            }
    
    def get_gold_price(self) -> Optional[Dict[str, Any]]:
        """Get current gold price in INR per gram using yfinance"""
        return self._get_commodity_price("GC=F", "gold")

    def get_silver_price(self) -> Optional[Dict[str, Any]]:
        """Get current silver price in INR per gram using yfinance"""
        return self._get_commodity_price("SI=F", "silver")

    def get_crude_price(self) -> Optional[Dict[str, Any]]:
        """Get current crude oil price in USD per barrel using yfinance"""
        return self._get_commodity_price("CL=F", "crude", convert_to_gram=False)

    def _get_commodity_price(self, ticker_sym: str, label: str, convert_to_gram: bool = True) -> Optional[Dict[str, Any]]:
        """Helper to fetch commodity price from yfinance"""
        cache_key = f"{label}_price"
        
        if self._is_cached(cache_key):
            value, _ = self.cache[cache_key]
            return value
            
        try:
            import yfinance as yf
            
            # 1. Get USD/INR rate (always needed for INR context)
            usd_inr_ticker = yf.Ticker("USDINR=X")
            usd_inr_hist = usd_inr_ticker.history(period="5d")
            usd_inr_rate = float(usd_inr_hist['Close'].iloc[-1].item()) if not usd_inr_hist.empty else 83.0
            
            # 2. Get Commodity Price
            comm_ticker = yf.Ticker(ticker_sym)
            comm_hist = comm_ticker.history(period="5d")
            
            if comm_hist.empty:
                return self._get_commodity_fallback(ticker_sym, label)
                
            price_usd = float(comm_hist['Close'].iloc[-1].item())
            open_usd = float(comm_hist['Open'].iloc[-1].item())
            
            if convert_to_gram:
                # Convert to INR per Gram (for Gold/Silver)
                price_per_gram_inr = (price_usd * usd_inr_rate) / 31.1034768
                
                price_data = {
                    'symbol': label.upper(),
                    'price': round(price_per_gram_inr, 2),
                    'price_per_gram_inr': round(price_per_gram_inr, 2),
                    'price_per_ounce_usd': round(price_usd, 2),
                    'change_percent': ((price_usd - open_usd) / open_usd * 100) if open_usd > 0 else 0,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'yfinance',
                    'currency': 'INR',
                    'units': 'gram'
                }
            else:
                # Keep as USD per Barrel (for Crude)
                price_data = {
                    'symbol': label.upper(),
                    'price': round(price_usd, 2),
                    'change_percent': ((price_usd - open_usd) / open_usd * 100) if open_usd > 0 else 0,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'yfinance',
                    'currency': 'USD',
                    'units': 'barrel'
                }
            
            self._cache_set(cache_key, price_data)
            return price_data
            
        except Exception as e:
            logger.error(f"Error fetching {label}: {e}")
            return self._get_commodity_fallback(ticker_sym, label)
    
    def _get_commodity_fallback(self, ticker_sym: str, label: str) -> Dict[str, Any]:
        """Fallback commodity prices when yfinance fails"""
        # Gold: 1,73,000 per 10g -> 17,300 per gram
        # Silver: 4,15,000 per kg -> 415 per gram
        # Crude: $85 per barrel
        fallbacks = {
            'GC=F': {'price': 17300.0, 'currency': 'INR', 'units': 'gram'},
            'SI=F': {'price': 415.0, 'currency': 'INR', 'units': 'gram'},
            'CL=F': {'price': 85.10, 'currency': 'USD', 'units': 'barrel'},
        }
        
        data = fallbacks.get(ticker_sym, {'price': 0, 'currency': 'USD', 'units': 'unknown'})
        
        return {
            'symbol': label.upper(),
            'price': data['price'],
            'price_per_gram_inr': data['price'] if data['currency'] == 'INR' else 0,
            'change_percent': 0.0,
            'timestamp': datetime.now().isoformat(),
            'source': 'fallback',
            'currency': data['currency'],
            'units': data['units']
        }
    
    def get_mutual_fund_nav(self, isin: str) -> Optional[Dict[str, Any]]:
        """Get mutual fund NAV (would integrate with actual MF data API)"""
        # Realistic MF data for common Indian funds
        funds = {
            'INF174K01V75': {'name': 'HDFC Equity Fund', 'nav': 621.45, 'one_yr_return': 16.8},
            'INF846K01364': {'name': 'Axis Growth Opportunities', 'nav': 185.50, 'one_yr_return': 18.5},
            'INF769K01FS2': {'name': 'Mirae Asset Large Cap Fund', 'nav': 78.30, 'one_yr_return': 15.2},
        }
        
        if isin in funds:
            fund = funds[isin]
            return {
                'isin': isin,
                'name': fund['name'],
                'nav': fund['nav'],
                'one_year_return': fund['one_yr_return'],
                'timestamp': datetime.now().isoformat(),
                'source': 'fund_database',
                'currency': 'INR'
            }
        
        return None
    
    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive market data for a symbol or index"""
        # Check if it's a known index
        known_indices = ['NIFTY50', 'SENSEX', 'BANKNIFTY', 'NIFTYMIDCAP', 'NIFTYNXT50']
        if symbol.upper() in known_indices:
            return self.get_index_data(symbol.upper())

        price = self.get_stock_price(symbol)
        
        # get_stock_price is now guaranteed to return a dict
        return {
            **price,
            'full_name': self.INDIAN_STOCKS.get(symbol, symbol),
            'market': 'NSE'
        }
    
    def _is_cached(self, key: str) -> bool:
        """Check cache validity"""
        if key not in self.cache:
            return False
        _, timestamp = self.cache[key]
        age = (datetime.now() - timestamp).total_seconds()
        return age < self.cache_duration
    
    def _cache_set(self, key: str, value: Any) -> None:
        """Set cache with timestamp"""
        self.cache[key] = (value, datetime.now())
