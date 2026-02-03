from flask import Flask, request, jsonify
from datetime import datetime
import uuid
import requests
import json

# Import our fixed modules
from models import db, ScamSession, ScamIntelligence
from detector import ScamDetector
from agent import HoneypotAgent

app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///honeypot_intelligence.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "hackathon_secret"

# Initialize DB with App
db.init_app(app)

# Initialize Logic Classes
detector = ScamDetector()
agent = HoneypotAgent()

# Create tables on startup
with app.app_context():
    db.create_all()


# --- Helper: Mandatory Callback to GUVI  ---
def send_guvi_callback(session, intel):
    """
    Sends the final report to the hackathon evaluation endpoint.
    """
    url = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

    # Helper to convert comma-string to list
    def to_list(s):
        return s.split(",") if s else []

    payload = {
        "sessionId": session.id,
        "scamDetected": session.scam_detected,
        "totalMessagesExchanged": session.turn_count,
        "extractedIntelligence": {
            "bankAccounts": to_list(intel.bank_accounts),
            "upilds": to_list(intel.upi_ids),  # Note: PDF typo 'upilds' handled here? keeping standard camelCase
            "upiIds": to_list(intel.upi_ids),  # sending both to be safe
            "phishingLinks": to_list(intel.phishing_links),
            "phoneNumbers": to_list(intel.phone_numbers),
            "suspiciousKeywords": to_list(intel.suspicious_keywords)
        },
        "agentNotes": "Automated Honeypot engagement completed."
    }

    try:
        # We wrap in try/except so our API doesn't crash if their server is down
        print(f"Sending Callback for Session {session.id}...")
        response = requests.post(url, json=payload, timeout=5)
        print(f"Callback Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Callback failed: {str(e)}")


# --- API Endpoint [cite: 13] ---
@app.route('/chat', methods=['POST'])
def chat():
    # 1. Security Check [cite: 19]
    api_key = request.headers.get('x-api-key') or request.headers.get('X-API-KEY')
    # Allowing "your_secret_hackathon_key" OR the example in doc
    if api_key not in ["your_secret_hackathon_key", "YOUR_SECRET_API_KEY"]:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    # 2. Parse Input according to PDF Section 6.1/6.2 [cite: 32, 48]
    # Structure: { "sessionId": "...", "message": { "text": "...", "sender": "..." } }
    session_id = data.get('sessionId')
    if not session_id:
        session_id = str(uuid.uuid4())  # Fallback if not provided

    message_data = data.get('message', {})
    user_text = message_data.get('text')

    # Fallback if user sends flat JSON (common mistake)
    if not user_text and 'text' in data:
        user_text = data['text']

    if not user_text:
        return jsonify({"error": "No message text provided"}), 400

    # 3. Retrieve or Create Session
    session = ScamSession.query.filter_by(id=session_id).first()
    if not session:
        session = ScamSession(id=session_id)
        db.session.add(session)
        # Create empty intelligence record
        intel = ScamIntelligence(session_id=session_id)
        db.session.add(intel)
        db.session.commit()

    # 4. Log User Message
    session.add_message("scammer", user_text)

    # 5. Analyze Message (Detector) [cite: 14]
    detection_result = detector.analyze_message(user_text, session)

    # 6. Generate Agent Response (Agent) [cite: 15]
    session.turn_count += 1
    agent_result = agent.generate_reply(session, user_text, detection_result)

    reply_text = agent_result['reply']
    session.add_message("agent", reply_text)
    db.session.commit()

    # 7. Check for Conversation End & Trigger Callback [cite: 121]
    # We trigger if the agent decides to end, OR if we have high risk and high turn count
    if agent_result.get('end_conversation') or (session.turn_count > 6 and session.scam_detected):
        intel = ScamIntelligence.query.filter_by(session_id=session.id).first()
        send_guvi_callback(session, intel)

    # 8. Return Response [cite: 102]
    return jsonify({
        "status": "success",
        "reply": reply_text,
        "sessionId": session_id,
        "scamDetected": session.scam_detected
    })

@app.route('/', methods=['GET'])
def home():
    return "Honeypot Active. Send POST requests to /chat"

if __name__ == '__main__':
    app.run(debug=True, port=5000)