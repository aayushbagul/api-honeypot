import re
from models import db, ScamIntelligence


class ScamDetector:

    def analyze_message(self, text, session):
        text_lower = text.lower()

        flags = []
        risk = 0
        extracted = {
            "upiIds": set(),
            "bankAccounts": set(),
            "phoneNumbers": set(),
            "phishingLinks": set(),
            "suspiciousKeywords": set()
        }

        # --- Scam indicators [cite: 9] ---
        scam_keywords = [
            "won", "prize", "lottery", "urgent",
            "account blocked", "verify now",
            "kyc", "upi", "bank", "suspension", "suspend"
        ]

        for word in scam_keywords:
            if word in text_lower:
                extracted["suspiciousKeywords"].add(word)
                risk += 10

        # --- Regex extraction [cite: 11] ---
        extracted["upiIds"].update(
            re.findall(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", text)
        )
        # Matches Indian mobile numbers and generic 10-digit numbers
        extracted["phoneNumbers"].update(
            re.findall(r"\+91[\-\s]?\d{10}|\b\d{10}\b", text)
        )
        extracted["phishingLinks"].update(
            re.findall(r"https?://\S+", text)
        )
        # Matches 9-18 digit numbers (potential bank accounts)
        extracted["bankAccounts"].update(
            re.findall(r"\b\d{9,18}\b", text)
        )

        # --- Risk escalation ---
        if extracted["upiIds"] or extracted["bankAccounts"]:
            flags.append("payment_request")
            risk += 30

        if extracted["phishingLinks"]:
            flags.append("phishing_link")
            risk += 40

        # If keyword + link/number/upi, almost certainly a scam
        if extracted["suspiciousKeywords"] and (extracted["phishingLinks"] or extracted["upiIds"]):
            risk += 20

        is_scam = risk >= 40  # Lowered threshold slightly to be more sensitive

        if is_scam:
            session.scam_detected = True

        # --- Persist intelligence ---
        self._save_intelligence(session.id, extracted)

        return {
            "is_scam": is_scam,
            "risk_score": risk,
            "flags": flags,
            "extracted_data": {
                k: list(v) for k, v in extracted.items()
            }
        }

    def _save_intelligence(self, session_id, data):
        # Find existing or create new
        intel = ScamIntelligence.query.filter_by(session_id=session_id).first()

        if not intel:
            intel = ScamIntelligence(session_id=session_id)
            db.session.add(intel)

        # Merge incrementally
        intel.upi_ids = self._merge(intel.upi_ids, data["upiIds"])
        intel.bank_accounts = self._merge(intel.bank_accounts, data["bankAccounts"])
        intel.phone_numbers = self._merge(intel.phone_numbers, data["phoneNumbers"])
        intel.phishing_links = self._merge(intel.phishing_links, data["phishingLinks"])
        intel.suspicious_keywords = self._merge(intel.suspicious_keywords, data["suspiciousKeywords"])

        db.session.commit()

    def _merge(self, existing, new_set):
        if not new_set:
            return existing or ""
        existing_set = set(existing.split(",")) if existing else set()
        # Filter out empty strings
        existing_set = {x for x in existing_set if x}
        combined = existing_set.union(new_set)
        return ",".join(combined)