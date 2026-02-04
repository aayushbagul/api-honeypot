from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize the database instance here to be shared
db = SQLAlchemy()

class ScamSession(db.Model):
    __tablename__ = "scam_sessions"

    id = db.Column(db.String(36), primary_key=True)
    turn_count = db.Column(db.Integer, default=0)
    scam_detected = db.Column(db.Boolean, default=False)
    # Storing conversation history as a simple text block for this hackathon level
    messages = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to intelligence
    intelligence = db.relationship("ScamIntelligence", backref="session", uselist=False, cascade="all, delete-orphan")

    def add_message(self, sender: str, text: str):
        entry = f"{sender}: {text}"
        if self.messages:
            self.messages += f"\n{entry}"
        else:
            self.messages = entry


class ScamIntelligence(db.Model):
    __tablename__ = "scam_intelligence"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('scam_sessions.id'), unique=True)

    # Storing sets as comma-separated strings
    upi_ids = db.Column(db.Text, default="")
    bank_accounts = db.Column(db.Text, default="")
    phone_numbers = db.Column(db.Text, default="")
    phishing_links = db.Column(db.Text, default="")
    suspicious_keywords = db.Column(db.Text, default="")

    agent_notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
