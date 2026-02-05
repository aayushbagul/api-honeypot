import random
import re


class HoneypotAgent:
    """
    Maintains the persona of a panicked victim.
    Refined for infinite looping and robust context detection.
    """

    def __init__(self, max_turns=None, narrative_limit=6):
        # We accept 'max_turns' to prevent crashes from legacy app.py calls,
        # but we don't use it for termination anymore.
        # 'narrative_limit' defines when we switch from Story Mode to Infinite Loop Mode.
        self.narrative_limit = narrative_limit

        # 1. CONTEXTUAL TRIGGERS
        # Using compiled regex for better performance and reliability
        self.triggers = {
            "deflect_otp": re.compile(r"(otp|code|pin|password|verif)", re.IGNORECASE),
            "tech_issue": re.compile(r"(link|url|click|website|app|download|apk|form)", re.IGNORECASE),
            "panic_response": re.compile(r"(police|jail|arrest|court|legal|fbi|cbi|rbi|warrant|case)", re.IGNORECASE),
            "financial_worry": re.compile(r"(account|bank|statement|balance|money|fund)", re.IGNORECASE),
            "stalling_pressure": re.compile(r"(hurry|fast|quick|immediately|now|urgent|asap)", re.IGNORECASE),
            "feign_compliance": re.compile(r"(details|info|send|share|disconnect|answer|reply|do it)", re.IGNORECASE),
            "confusion": re.compile(r"(why|who|what|how|reason|purpose)", re.IGNORECASE)
        }

        # 2. SCRIPT DATABASE
        # EXPANDED: Added ~30 new sentences to prevent repetition in the infinite loop.
        self.scripts = {
            # --- STORYLINE SCRIPTS (Early Conversation) ---
            "opening": [
                "Oh my god, really? I didn't do anything wrong. What is happening?",
                "Wait, is this serious? I just got this number. I'm panicked.",
                "Who is this? I haven't done anything illegal. Why are you messaging me?",
                "This is terrifying. Please tell me this is a mistake."
            ],
            "probe": [
                "I am so scared. Will I lose my money? Please help me fix this.",
                "Is my bank balance safe? I can't afford to have it blocked.",
                "I don't want any trouble with the police. What exactly do I need to do?",
            ],
            "bait": [
                "Okay, I trust you. I just want this resolved.",
                "I will do whatever you say to fix this. Please guide me.",
                "Okay, tell me the steps. I don't want my account frozen.",
                "I am a law-abiding citizen, please believe me.",
                "I don't want to lose my savings. I'll listen to you.",
                "Please stay on the line, I need your help to fix this."
            ],
            "extract": [
                "I'm trying to send the fee, but the app says 'Server Error'. Do you have a direct Bank Account number or UPI ID instead?",
                "The link isn't loading. Can I just transfer directly to your account? What is the account number?",
                "My payment app is glitching. If you give me your UPI ID, I can try sending it from my wife's phone.",
                "It's asking for beneficiary details. Can you share your Account Number and IFSC?"
            ],
            # MASSIVELY EXPANDED STALL LIST
            "stall": [
                "Hold on, my internet is very slow... it's buffering.",
                "One second, let me find my reading glasses, I can't see the screen clearly.",
                "Sorry, my battery is 1%, let me run and get a charger. Don't hang up.",
                "My screen froze. I'm restarting the phone. Please wait 1 minute.",
                "My hands are shaking so much, I keeps typing the wrong digits. Give me a moment.",
                "The app just crashed. I am reopening it. Please stay online.",
                "My wife is calling on the other line, let me reject it quickly.",
                "The circle is just spinning round and round. Is the server down?",
                "I dropped my phone in my panic, the screen is cracked. Hard to read.",
                "Wait, someone is ringing the doorbell. It might be the postman. One second.",
                "My glasses are foggy, I'm wiping them so I can read the card number.",
                "The keypad is stuck on the screen. It won't let me type.",
                "It says 'Please update application' before I can proceed. Updating now...",
                "I can't find the 'send' button. Is it at the top or bottom?",
                "My son is asking me something, let me just tell him to go away.",
                "The wifi just disconnected. Let me switch to mobile data.",
                "It's asking for a fingerprint now, but my finger is wet.",
                "I typed the number wrong again, deleting it... sorry, I'm nervous.",
                "Wait, I left my card in the other room. Running to get it.",
                "The screen went dim, I'm trying to brighten it.",
                "Wait, I clicked the wrong thing. Going back to the main menu.",
                "It says 'Loading secure gateway', still spinning...",
                "My fingers are too big for these tiny buttons, I keep hitting space.",
                "The app closed itself again. Why is this happening?",
                "I'm entering the numbers... 4... 5... wait, was it 5 or 6?",
                "It's asking me to rotate the phone for security view.",
                "Hold on, a WhatsApp notification covered the button.",
                "I'm shivering, sorry, typing is very slow right now.",
                "Just a moment, I am finding a pen to write down what you said.",
                "The page is completely white. Is it supposed to be white?"
            ],

            # --- CONTEXT REACTION SCRIPTS ---
            "deflect_otp": [
                "I didn't get any code yet. Should I wait?",
                "My messages aren't coming through. Signal is weak here.",
                "It says 'Do not share this code'. Is it safe to give it to you?",
                "Wait, a message just flashed but disappeared. Send it again?",
                "I got a code for a food delivery app, is that the one?",
                "My inbox is full, let me delete some old messages to receive it."
            ],
            "tech_issue": [
                "I clicked it but it says 'Site cannot be reached'.",
                "The link is not opening. Is there another way?",
                "I don't know how to download that. I am not very good with technology.",
                "It says 'File Corrupted'. Can we do this without downloading the app?",
                "My browser says 'Connection Not Private'. Should I be worried?",
                "It's downloading something but it's stuck at 0%.",
                "Do I click 'Allow' or 'Block'? It's asking for permission."
            ],
            "panic_response": [
                "Please don't involve the police! I am a respectable citizen.",
                "I am literally crying right now. Please help me stop the warrant.",
                "I cannot go to jail. I have children. Please help me."
            ],
            "financial_worry": [
                "I have my life savings in there. Is it safe?",
                "If I do this, will my account be unblocked immediately?",
                "I just want to secure my money. Please tell me it's safe."
            ],
            "stalling_pressure": [
                "I am trying! Please don't yell at me, I'm nervous.",
                "I'm going as fast as I can, but my phone is very old.",
                "Please be patient, I am doing exactly what you said."
            ],
            "feign_compliance": [
                "Yes, yes, I am doing it right now. Just a moment.",
                "Okay, I am looking for it now.",
                "I am listening, please don't disconnect.",
                "I am typing it in, please wait."
            ],
            "confusion": [
                "I don't understand what is going on. I am just a normal person.",
                "Why is this happening to me? I am so confused.",
                "I am trying to answer, but I am very scared.",
                "Please just tell me how to fix this, I don't know anything else.",
                "Why is it so complicated? I thought this was simple.",
                "Can't you just unlock it from your end? Why do I need to do this?",
                "My nephew usually does this for me. I am lost.",
                "I am getting a headache from this panic."
            ],

            "fallback": [
                "Okay, understood.",
                "What should I do next?",
                "I am listening.",
                "Go ahead."
            ]
        }

    def _get_msg(self, key):
        """Helper to pick a random message from the list for a given key."""
        options = self.scripts.get(key, self.scripts["fallback"])
        if isinstance(options, list):
            return random.choice(options)
        return options

    def _detect_context(self, user_text):
        """Scans user text for triggers to override the turn-based logic."""
        if not user_text:
            return None

        # Check against compiled regex triggers
        for script_key, pattern in self.triggers.items():
            if pattern.search(user_text):
                return script_key
        return None

    def generate_reply(self, session, user_text, meta_data=None, intelligence_context=None):
        """
        Generates response using a Hybrid approach:
        1. Contextual Triggers (Reaction) - Priority over story to fix 'out of context' issues.
        2. Intelligence gathering (Stall if won).
        3. Turn-Based Story (Narrative).
        4. Infinite Loop (Stall forever).
        """

        current_turn = session.turn_count

        # Intelligence tracking
        has_intel = intelligence_context and (
                intelligence_context.get('has_bank') or
                intelligence_context.get('has_upi') or
                intelligence_context.get('has_phone')
        )

        reply = ""
        state = "active"

        # --- LOGIC LAYER 1: CONTEXTUAL OVERRIDES ---
        # We check this FIRST to ensure we respond to questions/threats immediately.
        context_key = self._detect_context(user_text)

        if context_key:
            # If it's the opening turns, only react if it's a Panic trigger.
            # Otherwise, ignore context and play the "Who is this?" card.
            if current_turn > 1 or context_key == "panic_response":
                reply = self._get_msg(context_key)
                state = f"reacting_{context_key}"
                return self._response(reply, state=state)

        # --- LOGIC LAYER 2: INTELLIGENCE CHECK ---
        # If we have what we want, we just stall forever.
        if has_intel:
            reply = self._get_msg("stall")
            state = "stalling_forever"
            return self._response(reply, state=state)

        # --- LOGIC LAYER 3: TURN-BASED STORY ARC ---
        # Fallback if no specific context was triggered.

        if current_turn <= 1:
            reply = self._get_msg("opening")
            state = "opening"

        elif current_turn == 2:
            reply = self._get_msg("probe")
            state = "probing"

        elif current_turn == 3:
            reply = self._get_msg("extract")
            state = "extraction"

        elif current_turn == 4:
            reply = self._get_msg("bait")
            state = "baiting"

        elif current_turn == 5:
            reply = self._get_msg("extract")
            state = "extraction"

        # --- LOGIC LAYER 4: INFINITE LOOP ---
        # After the narrative, we cycle forever.
        else:
            # Randomly mix Stalling, Confusion, and Baiting.
            # Weighted choice: mostly stall (60%), some confusion (20%), some bait (20%)
            loop_options = ["stall", "stall", "stall", "confusion", "bait"]
            selected_mode = random.choice(loop_options)
            reply = self._get_msg(selected_mode)
            state = f"infinite_loop_{selected_mode}"

        return self._response(reply, state=state)

    def _response(self, text, end=False, state="active"):
        # Force end=False to prevent any accidental termination signal
        return {
            "reply": text,
            "end_conversation": False,
            "agent_state": state
        }
