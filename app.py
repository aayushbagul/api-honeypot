import os
import uuid
import logging
from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests

# Import internal modules
from models import db, ScamSession, ScamIntelligence
from detector import ScamDetector
from agent import HoneypotAgent

# Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'honeypot_intelligence.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CONFIGURATION
CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

# IMPORTANT: Replace with your actual API key
API_KEYS = "MlYp-BYmcd7ebj1ospIEI387BJuIRmJYBOLyeIkj8NI"


def check_auth(headers):
    """Validate API Key from headers (Case Insensitive)."""
    key = headers.get('x-api-key') or headers.get('X-API-KEY')
    if key not in API_KEYS:
        logger.warning(f"Unauthorized access attempt with key: {key}")
        return False
    return True


def parse_input(data):
    """Parse input according to Tasks.md specification."""
    text = None
    
    # Priority 1: Tasks.md specified format - message.txt_message
    if 'message' in data and isinstance(data['message'], dict):
        text = data['message'].get('txt_message')
        if not text:
            text = data['message'].get('text')
    
    # Priority 2: Flat format fallbacks
    if not text:
        text = data.get('txt_message')
    if not text:
        text = data.get('text')
    
    return text


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'status': 'error', 'message': 'Bad Request: Invalid input format'}), 400)


@app.errorhandler(401)
def unauthorized(error):
    return make_response(jsonify({'status': 'error', 'message': 'Unauthorized: Invalid API Key'}), 401)


@app.errorhandler(500)
def internal_error(error):
    return make_response(jsonify({'status': 'error', 'message': 'Internal Server Error'}), 500)


@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "message": "Honeypot Active. POST to /chat to engage.",
        "endpoints": {
            "chat": "/chat",
            "health": "/"
        }
    })


@app.route('/health', methods=['GET'])
def health():
    """Additional health check"""
    return jsonify({"status": "healthy", "service": "honeypot"})


@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint for honeypot interaction."""
    
    logger.info("Received request to /chat")
    
    # 1. Security Check
    if not check_auth(request.headers):
        logger.warning("Authentication failed")
        return jsonify({"status": "error", "reply": "Invalid or missing API Key"}), 401

    # 2. Parse Payload
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            logger.error("Invalid JSON payload")
            return jsonify({"status": "error", "reply": "Invalid JSON payload"}), 400
    except Exception as e:
        logger.error(f"JSON parsing error: {e}")
        return jsonify({"status": "error", "reply": "Malformed JSON"}), 400

    # Extract Core Data
    session_id = data.get('sessionId') or data.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())

    user_text = parse_input(data)
    if not user_text:
        logger.error("No message text in payload")
        return jsonify({"status": "error", "reply": "No message text provided"}), 400

    logger.info(f"Processing message for session {session_id}: {user_text[:50]}...")

    # Extract Metadata and History
    meta_data = data.get('meta_data', {})
    conversation_history = data.get('conversation_history', [])

    # 3. Session Management
    session = None
    try:
        session = ScamSession.query.filter_by(id=session_id).first()
    except Exception as e:
        logger.warning(f"DB Read Error: {e}")

    if not session:
        session = ScamSession(id=session_id)
        
        # Import conversation history if provided
        if conversation_history:
            for hist_msg in conversation_history:
                if isinstance(hist_msg, dict):
                    sender = hist_msg.get('sender', 'unknown')
                    text = hist_msg.get('txt_message') or hist_msg.get('text', '')
                    if text:
                        session.add_message(sender, text)
        
        db.session.add(session)
        intelligence = ScamIntelligence(session_id=session_id)
        db.session.add(intelligence)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"DB Commit Failed: {e}")
    else:
        intelligence = session.intelligence

    # 4. Message Logging & Analysis
    try:
        session.add_message("scammer", user_text)

        # Find this section around line 160 in your app.py
        detector = ScamDetector()
        analysis_result = detector.analyze_message(user_text, session, intelligence)

        # FIX: Only update to True, never reset to False
        if analysis_result['is_scam']:
            session.scam_detected = True #

        # 5. Agent Response Generation
        agent = HoneypotAgent(max_turns=8)

        # Pass intelligence context
        current_intelligence_context = {
            'has_bank': bool(intelligence.bank_accounts),
            'has_upi': bool(intelligence.upi_ids),
            'has_phone': bool(intelligence.phone_numbers),
            'has_link': bool(intelligence.phishing_links)
        }

        reply_data = agent.generate_reply(
            session,
            user_text,
            meta_data=meta_data,
            intelligence_context=current_intelligence_context
        )

        agent_reply = reply_data['reply']
        session.add_message("agent", agent_reply)
        session.turn_count += 1

        # Commit state updates
        db.session.commit()

        # 6. Callback Logic
        has_intelligence = (
            bool(intelligence.bank_accounts) or 
            bool(intelligence.upi_ids) or 
            bool(intelligence.phone_numbers) or
            bool(intelligence.phishing_links)
        )
        
        should_report = (
            session.scam_detected and 
            session.turn_count >= 6 and 
            has_intelligence
        ) or reply_data['end_conversation']

        if should_report:
            send_guvi_callback(session, intelligence, analysis_result)

        # 7. Final Response
        logger.info(f"Sending reply for session {session_id}")
        return jsonify({
            "status": "success",
            "reply": agent_reply
        })

    except Exception as e:
        logger.error(f"Processing Error: {e}", exc_info=True)
        return jsonify({"status": "error", "reply": str(e)}), 500


def to_list(csv_str):
    """Helper to convert CSV string to list, filtering empties."""
    if not csv_str:
        return []
    return [item.strip() for item in csv_str.split(',') if item.strip()]


def send_guvi_callback(session, intelligence, analysis_result):
    """Sends final report to GUVI evaluation endpoint."""
    try:
        tactics = ", ".join(analysis_result.get('flags', []))
        notes = f"Honeypot engagement concluded. Threat detected. Tactics identified: {tactics or 'None'}."

        payload = {
        "sessionId": session.id,
        "scamDetected": session.scam_detected,
        "totalMessagesExchanged": session.turn_count,
        "extractedIntelligence": {
        "bank account": to_list(intelligence.bank_accounts),
        "upiid": to_list(intelligence.upi_ids),
        "phishing links": to_list(intelligence.phishing_links),
        "phone numbers": to_list(intelligence.phone_numbers),
        "suspicious keywords": to_list(intelligence.suspicious_keywords)
        },
        "agentNotes": notes
        }

        logger.info(f"Sending callback to {CALLBACK_URL}")
        logger.info(f"Payload: {payload}")
        
        response = requests.post(CALLBACK_URL, json=payload, timeout=5)
        logger.info(f"Callback sent. Status: {response.status_code}, Response: {response.text}")

    except requests.exceptions.Timeout:
        logger.error("Callback timed out after 5 seconds.")
    except Exception as e:
        logger.error(f"Failed to send callback: {e}")


# Database Creation Hook
with app.app_context():
    try:
        db.create_all()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

if __name__ == '__main__':
    # Get port from environment variable (Render uses PORT env var)
    port = int(os.environ.get('PORT', 5000))
    
    # Check if API keys have been updated
    if "your_secret_hackathon_key" in API_KEYS and os.environ.get('HACKATHON_API_KEY') is None:
        logger.warning("="*60)
        logger.warning("WARNING: Using default API keys!")
        logger.warning("Set HACKATHON_API_KEY environment variable")
        logger.warning("="*60)
    
    # Render requires host='0.0.0.0' to accept external connections
    app.run(host='0.0.0.0', port=port, debug=False)

