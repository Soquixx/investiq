import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, session
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Internal Imports
from database.db import db
from database.models import User
from config import config

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object(config[config_name])
    
    # Configure Logging
    logging.basicConfig(
        level=app.config.get('LOG_LEVEL', logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Initialize Extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from routes.main_routes import main_bp
    from routes.auth_routes import auth_bp
    from routes.api_routes import api_bp
    from routes.dashboard_routes import dashboard_bp
    from routes.advisory_routes import advisory_bp
    from routes.chatbot_routes import chatbot_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(advisory_bp, url_prefix='/advisory')
    app.register_blueprint(chatbot_bp)

    # Global Template Context
    @app.context_processor
    def inject_now():
        return {
            'now': datetime.utcnow(),
            'app_name': 'InvestIQ',
            'current_year': datetime.now().year
        }

    # Session Security
    @app.before_request
    def session_management():
        session.permanent = True
        app.permanent_session_lifetime = timedelta(hours=2)

    # Error Pages
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        return render_template('500.html'), 500

    # Utility Favicon Route
    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    return app

# This creates the 'app' object at the top level so 'gunicorn app:app' works.
# It checks for a FLASK_CONFIG env var, otherwise defaults to 'default'.
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == "__main__":
    # Use the 'app' object created above
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False))
