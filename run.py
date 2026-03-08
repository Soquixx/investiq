"""
Main entry point for the InvestIQ Application.
Includes automated database initialization and health checks.
"""
import os
from app import create_app
from database.db import db
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = create_app()

def run_health_check():
    """Verify that all critical components are ready"""
    print("\n" + "="*50)
    print("        INVESTIQ SYSTEM HEALTH CHECK")
    print("="*50)
    
    # 1. Check API Keys
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print(f"✅ Gemini API Key:   Configured (Starts with: {gemini_key[:8]}...)")
    else:
        print(f"❌ Gemini API Key:   MISSING (AI analysis will use rule-based fallback)")

    # 2. Check ML Models
    # Updated to check for a core model from the new pipeline
    model_path = os.path.join(os.path.dirname(__file__), "models", "investor_classifier.pkl")
    if os.path.exists(model_path):
        print(f"✅ ML Models:       Found in /models folder")
    else:
        print(f"❌ ML Models:       NOT FOUND (Check /models/ folder)")

    # 3. Check Database
    db_path = os.path.join(os.path.dirname(__file__), "investiq.db")
    print(f"ℹ️  Database Path:   {db_path}")
    
    print("="*50 + "\n")

if __name__ == "__main__":
    with app.app_context():
        # This will create the .db file if it doesn't exist
        
        db.create_all()
        
    
    run_health_check()
    
    # Start the Flask development server
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print(f"🚀 Starting server on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)