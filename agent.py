
import random


class HoneypotAgent:
    """
    Maintains the persona and handles turn-taking logic.
    Acts as a panicked victim from the very first message.
    """

    def __init__(self, max_turns=8):
        self.max_turns = max_turns

        # Removed "neutral" responses - honeypot should NEVER sound suspicious
        self.scripts = {
            "opening": [
                "Oh my god, really? I didn't do anything wrong. What should I do?",
                "Wait, is this serious? I just got this number. I'm panicked.",
                "Oh no! I haven't done anything illegal. Why is this happening?",
                "This is terrifying. Please tell me this is a mistake.",
                "What?! I'm so scared. Please help me understand what's going on."
            ],
            "probe": [
                "I am so scared. Will I lose my money? Please help me fix this.",
                "Is my bank balance safe? I can't afford to have it blocked.",
                "I am really worried about my savings. What exactly do I need to do?",
                "This sounds urgent. I don't want any legal trouble. Please help.",
                "My hands are shaking. What did I do wrong? Can you fix this for me?"
            ],
            "bait": [
                "Okay, I will do whatever you say. I just want my account safe.",
                "I understand. Please guide me, I trust you to fix this.",
                "Okay, tell me the steps. I want to resolve this immediately.",
                "I am ready to verify. Just tell me what information you need.",
                "Yes yes, I'll cooperate fully. Just please don't block my account."
            ],
            "extract": [
                "I am trying to send the money but the app is asking for details. Can I send it to a bank account or UPI directly? Please share the details.",
                "My app is glitching. Do you have a direct UPI ID or account number I can transfer to instead?",
                "It says 'Server Error'. Is there a specific bank account number I should use for the verification fee?",
                "The payment link isn't opening. Can you just give me your UPI ID? I'll send it from my other app.",
                "Where should I send the payment? Give me your account details or UPI ID and I'll transfer right now.",
                "Should I send it to your bank account? What's the account number? Or do you prefer UPI?"
            ],
            "stall": [
                "Hold on, my internet is slow. Just writing it down now...",
                "One second, the app is loading... it's just spinning.",
                "Wait, I need to find my reading glasses to read the card number. Just a moment.",
                "Hang on, my battery is low, let me plug in the charger quickly.",
                "Sorry, my wife is calling me. Give me 30 seconds...",
                "The screen went black, restarting my phone. Don't disconnect please."
            ],
            "fallback": [
                "Okay, please tell me the next step.",
                "I am listening. Go ahead.",
                "What should I do next?",
                "Okay, understood. Continue please."
            ]
        }

    def _get_msg(self, key):
        """Helper to pick a random message from the list for a given key."""
        options = self.scripts.get(key, self.scripts["fallback"])
        if isinstance(options, list):
            return random.choice(options)
        return options

    def generate_reply(self, session, user_text, meta_data=None, intelligence_context=None):
        """
        Generates the next response based on turn count.
        Follows a tighter script to extract intelligence faster.
        """

        # Check Termination
        if session.turn_count >= self.max_turns:
            return self._response("Okay, I have done it. Please check.", end=True, state="completed")

        current_turn = session.turn_count

        # Intelligence tracking
        has_intel = intelligence_context and (
            intelligence_context.get('has_bank') or
            intelligence_context.get('has_upi') or
            intelligence_context.get('has_phone') or
            intelligence_context.get('has_link')
        )

        reply = ""
        state = ""

        # TURN-BY-TURN SCRIPT
        # Turn 1: Immediate panic (no neutral response)
        if current_turn == 0 or current_turn == 1:
            reply = self._get_msg("opening")
            state = "opening"

        # Turn 2: Express fear, ask what to do
        elif current_turn == 2:
            reply = self._get_msg("probe")
            state = "probing"

        # Turn 3: Start extraction early
        elif current_turn == 3:
            if has_intel:
                # Already got what we need, stall
                reply = self._get_msg("stall")
                state = "stalling"
            else:
                # First extraction attempt
                reply = self._get_msg("extract")
                state = "extraction"

        # Turn 4: Second extraction attempt or bait
        elif current_turn == 4:
            if has_intel:
                reply = self._get_msg("bait")
                state = "baiting"
            else:
                # Try extraction again with different wording
                reply = self._get_msg("extract")
                state = "extraction"

        # Turn 5: Stall or continue baiting
        elif current_turn == 5:
            if has_intel:
                reply = self._get_msg("stall")
                state = "stalling"
            else:
                reply = self._get_msg("bait")
                state = "baiting"

        # Turn 6+: Maximum stalling to keep them engaged
        elif current_turn >= 6:
            reply = self._get_msg("stall")
            state = "stalling"

        else:
            reply = self._get_msg("fallback")
            state = "active"

        return self._response(reply, state=state)

    def _response(self, text, end=False, state="active"):
        return {
            "reply": text,
            "end_conversation": end,
            "agent_state": state
        }
