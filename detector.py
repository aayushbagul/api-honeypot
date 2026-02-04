import re


class ScamDetector:

    def __init__(self):
        # Expanded suspicious keywords library
        self.keywords = {
            "urgent", "immediately", "blocked", "suspended", "kyc",
            "verify", "pan card", "aadhaar", "aadhar", "lottery", "prize",
            "winner", "expire", "expired", "unauthorized", "irs", "police",
            "bank", "rbi", "customer care", "refund", "cashback",
            "wallet", "otp", "pin", "cvv", "atm", "card",
            "account", "payment", "transfer", "freeze", "frozen",
            "legal action", "arrest", "warrant", "customs", "tax",
            "confirm", "update", "link", "click", "reset password",
            "secure", "verify now", "act now", "limited time"
        }

        # Improved Regex Patterns
        # UPI: handle@bank format (more strict)
        self.upi_pattern = r'\b[a-zA-Z0-9.\-_]{3,}@[a-zA-Z]{3,}\b'

        # Indian Phone: +91 or start with 6-9, 10 digits
        self.phone_pattern = r'(?:\+91[\s\-]?)?[6-9]\d{9}\b'

        # Bank Account: 9-18 digits (more strict boundaries)
        self.bank_pattern = r'\b\d{9,18}\b'

        # Links: HTTP/HTTPS with better capture
        self.link_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        
        # Additional patterns for better detection
        self.ifsc_pattern = r'\b[A-Z]{4}0[A-Z0-9]{6}\b'  # IFSC codes

    def analyze_message(self, text, session, intelligence_record):
        """
        Analyzes text, updates the intelligence record, and calculates risk.
        Returns a summary dict.
        """
        if not text:
            return {"is_scam": False, "risk_score": 0, "flags": [], "extracted_data": {}}

        text_lower = text.lower()
        risk_score = 0
        flags = []

        # Extraction Phase
        extracted = {
            "suspiciousKeywords": set(),
            "upiIds": set(re.findall(self.upi_pattern, text)),
            "phoneNumbers": set(re.findall(self.phone_pattern, text)),
            "bankAccounts": set(re.findall(self.bank_pattern, text)),
            "phishingLinks": set(re.findall(self.link_pattern, text)),
            "ifscCodes": set(re.findall(self.ifsc_pattern, text.upper()))
        }

        # Keyword Analysis - Multi-word phrases
        keyword_matches = []
        for word in self.keywords:
            if word in text_lower:
                extracted["suspiciousKeywords"].add(word)
                keyword_matches.append(word)
                risk_score += 10

        # High-risk keyword combinations
        urgency_words = {"urgent", "immediately", "now", "quickly", "hurry"}
        threat_words = {"blocked", "suspended", "frozen", "arrest", "legal action"}
        verify_words = {"verify", "confirm", "update", "click", "link"}
        
        has_urgency = any(w in text_lower for w in urgency_words)
        has_threat = any(w in text_lower for w in threat_words)
        has_verify = any(w in text_lower for w in verify_words)
        
        # Combination scoring
        if has_urgency and has_threat:
            risk_score += 20
            flags.append("urgency_with_threat")
        
        if has_verify and has_threat:
            risk_score += 15
            flags.append("verify_with_threat")

        # Payment Request Detection
        if extracted["upiIds"] or extracted["bankAccounts"] or extracted["ifscCodes"]:
            risk_score += 30
            flags.append("payment_request")

        # Phishing Link Detection
        if extracted["phishingLinks"]:
            risk_score += 40
            flags.append("phishing_link")
            
            # Extra points if link + urgency
            if has_urgency:
                risk_score += 10

        # Contact Sharing
        if extracted["phoneNumbers"]:
            risk_score += 10
            flags.append("contact_sharing")

        # Heuristic: Multiple indicators = high confidence scam
        indicator_count = sum([
            bool(extracted["upiIds"]),
            bool(extracted["bankAccounts"]),
            bool(extracted["phishingLinks"]),
            bool(keyword_matches),
            has_urgency,
            has_threat
        ])
        
        if indicator_count >= 3:
            risk_score += 20
            flags.append("multiple_indicators")

        # Threshold for scam detection
        is_scam = risk_score >= 40

        # Persistence Phase (Side-effect)
        self._save_intelligence(intelligence_record, extracted)

        return {
            "is_scam": is_scam,
            "risk_score": risk_score,
            "flags": flags,
            "extracted_data": extracted
        }

    def _save_intelligence(self, record, extracted_data):
        """Helper to append unique items to the DB record without duplication."""
        record.upi_ids = self._merge(record.upi_ids, extracted_data["upiIds"])
        record.bank_accounts = self._merge(record.bank_accounts, extracted_data["bankAccounts"])
        record.phone_numbers = self._merge(record.phone_numbers, extracted_data["phoneNumbers"])
        record.phishing_links = self._merge(record.phishing_links, extracted_data["phishingLinks"])
        record.suspicious_keywords = self._merge(record.suspicious_keywords, extracted_data["suspiciousKeywords"])

    def _merge(self, current_str, new_set):
        """Merges a CSV string with a new set of items, returning unique CSV."""
        if not current_str:
            current_items = set()
        else:
            current_items = set(x.strip() for x in current_str.split(',') if x.strip())

        merged = current_items.union(new_set)
        return ",".join(sorted(merged))  # Sorted for consistency
