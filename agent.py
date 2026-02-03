import re


class HoneypotAgent:
    """
    Maintains the persona and handles turn-taking logic. [cite: 10]
    """

    def __init__(self):
        # We limit the conversation to ensure we eventually report back to GUVI
        self.max_turns = 8

        self.turn_handlers = {
            1: self._turn_opening,
            2: self._turn_probe,
            3: self._turn_bait,
            4: self._turn_bait,
            5: self._turn_extract,
            6: self._turn_extract,
            7: self._turn_stall
        }

    def generate_reply(self, session, user_message, detection_result):
        # Increment turn count in session (handled by caller, but we use the value)
        current_turn = session.turn_count

        # Stop condition [cite: 142]
        if current_turn >= self.max_turns:
            return self._response(
                "Okay, I will try to process this now. Give me a moment.",
                end=True,
                state="completed"
            )

        # Logic selector
        handler = self.turn_handlers.get(current_turn, self._turn_fallback)

        # If scam not detected yet, act confused but don't bait hard
        if not session.scam_detected:
            return self._response("I'm not sure I understand. Can you explain why this is urgent?", state="neutral")

        return handler(user_message, detection_result)

    # -------------------------
    # Turn Handlers
    # -------------------------
    def _turn_opening(self, text, detection):
        return self._response(
            "Oh my god, really? I didn't do anything wrong. What should I do?",
            state="opening"
        )

    def _turn_probe(self, text, detection):
        return self._response(
            "I am very worried. Will I lose my money? Please help me fix this.",
            state="probing"
        )

    def _turn_bait(self, text, detection):
        return self._response(
            "Okay, I want to resolve this immediately. Do you need my details?",
            state="baiting"
        )

    def _turn_extract(self, text, detection):
        return self._response(
            "I am having trouble with the app. Can I send it to a bank account or UPI directly? Please share the details.",
            state="extraction"
        )

    def _turn_stall(self, text, detection):
        return self._response(
            "Hold on, my internet is slow. Just writing it down now...",
            state="stalling"
        )

    def _turn_fallback(self, text, detection):
        return self._response(
            "Okay, please tell me the next step.",
            state="engaging"
        )

    def _response(self, message, end=False, state="engaging"):
        return {
            "reply": message,
            "end_conversation": end,
            "agent_state": state
        }