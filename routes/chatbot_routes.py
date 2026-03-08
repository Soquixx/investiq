from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from services.chatbot_service import ChatbotService

chatbot_bp = Blueprint('chatbot', __name__)
chatbot_service = ChatbotService()

@chatbot_bp.route('/chat')
@login_required
def chat_index():
    """Renders the chatbot interface."""
    return render_template('chat.html')

@chatbot_bp.route('/chat/message', methods=['POST'])
@login_required
def chat_message():
    """Handles chat messages via AJAX."""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    user_message = data.get('message')
    history = data.get('history', []) # Expecting a list of {role: 'user/assistant', content: '...'}
    
    # Add the current user message to history
    history.append({'role': 'user', 'content': user_message})

    # Prepare user profile context (READ ONLY)
    user_profile = {
        'age': current_user.age,
        'risk_tolerance': current_user.risk_tolerance,
        'investment_horizon': current_user.investment_horizon,
        'total_portfolio_value': current_user.get_total_portfolio_value()
    }

    # Get response from service
    ai_response = chatbot_service.get_chat_response(history, user_profile)

    return jsonify({
        'response': ai_response
    })
