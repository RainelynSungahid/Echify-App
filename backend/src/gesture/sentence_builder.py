# backend/src/gesture/sentence_builder.py
"""
SentenceBuilder — updated for 34-label FSL dataset (added NAME).

Labels by category:
  POLITENESS : HELLO, PLEASE, THANKS, SORRY, GOODBYE, MORNING, AFTERNOON
  ACTIONS    : WANT, HELP, GO, EAT, SLEEP, UNDERSTAND, KNOW
  QUESTIONS  : HOW, WHAT, WHERE, WHY, WHO
  PEOPLE     : I, YOU, ME, FRIEND, FAMILY
  ANSWERS    : YES, NO, OKAY, GOOD, BAD
  TIME       : TODAY
  PLACE      : HOME, HERE, FROM
  IDENTITY   : NAME
"""

import time
from typing import List, Optional, Tuple, Set
 
 
class SentenceBuilder:

    def __init__(self, short_pause: float = 0.8, long_pause: float = 2.2, max_tokens: int = 25):
        self.short_pause = short_pause
        self.long_pause = long_pause
        self.max_tokens = max_tokens
 
        self.tokens: List[str] = []
        self.pause_start_time: Optional[float] = None
        self.last_token_time: Optional[float] = None
 
        # ── Word Categories ──────────────────────
        self.subjects = {"I", "ME", "YOU"}
        self.verbs = {"WANT", "HELP", "GO", "EAT", "SLEEP", "UNDERSTAND", 
                      "KNOW", "LIKE", "LOVE", "NEED"}
        self.objects = {"HOME", "FAMILY", "FRIEND", "NAME", "FOOD"}
        self.modifiers = {"GOOD", "PLEASE", "SORRY", "THANKS", "YES", "NO", 
                         "OKAY", "TODAY", "HERE", "FROM"}
        self.questions = {"HOW", "WHAT", "WHERE", "WHY", "WHO"}
        self.greetings = {"HELLO", "GOODBYE", "MORNING", "AFTERNOON"}
        self.locations = {"HOME", "HERE", "FROM"}
        self.time_words = {"TODAY", "MORNING", "AFTERNOON"}
        
        self.ignore_tokens = {
            "WAITING", "COLLECTING...", "BUFFERING...", "UNKNOWN",
            "WAITING...", "SIGNING...", "TOO SHORT / IGNORED", ""
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Token collection
    # ──────────────────────────────────────────────────────────────────────────
    def add_token(self, token: str) -> Optional[Tuple[str, str]]:
        now   = time.time()
        token = token.strip().upper()

        if token in self.ignore_tokens:
            return None

        # skip immediate consecutive duplicates
        # if self.tokens and self.tokens[-1] == token:
        #     self.last_token_time = now
        #     return None

        self.tokens.append(token)
        self.last_token_time = now

        if len(self.tokens) >= self.max_tokens:
            return self.finalize()

        return None

    def update_pause(self, hands_detected: bool) -> Optional[Tuple[str, str]]:
        now = time.time()

        if hands_detected:
            self.pause_start_time = None
            return None

        if self.pause_start_time is None:
            self.pause_start_time = now
            return None

        elapsed = now - self.pause_start_time

        # ❌ REMOVE short pause trigger
        # if elapsed >= self.short_pause and len(self.tokens) >= 3:
        #     return self.finalize()

        # ✅ ONLY finalize on long pause
        if elapsed >= self.long_pause and self.tokens:
            return self.finalize()

        return None

    def finalize(self) -> Tuple[str, str]:
        raw = " ".join(self.tokens).strip()
        eng = self.expand(raw)
        self.tokens           = []
        self.pause_start_time = None
        self.last_token_time  = None
        return raw, eng

    def reset(self):
        self.tokens           = []
        self.pause_start_time = None
        self.last_token_time = None
 
    # ─────────────────────────────────────────
    # Intelligent Sentence Construction
    # ─────────────────────────────────────────
    def expand(self, raw: str) -> str:
        toks = [t for t in raw.upper().split() if t]
        if not toks:
            return ""
        
        # --- NEW LOGIC: Only use exact fixes if we have a small, unique set of words ---
        # This allows repeats like MORNING MORNING to skip the "Exact Match" 
        # and go to the fallback where they stay repeated.
        token_set = set(toks)
        
        # 1. HANDLE GREETING/PHRASE PAIRING
        processed_toks = []
        skip_next = False
        for i in range(len(toks)):
            if skip_next:
                skip_next = False
                continue
            if toks[i] == "GOOD" and i + 1 < len(toks) and toks[i+1] in {"MORNING", "AFTERNOON"}:
                processed_toks.append(f"GOOD {toks[i+1]}")
                skip_next = True
            else: processed_toks.append(toks[i])

        # 2. EXACT PATTERN MATCHING (ONLY if words aren't intentionally repeated)
        # If the number of tokens is much larger than the set, user is repeating for emphasis.
        if len(toks) == len(token_set):
            # Politeness / Single Words
            if token_set == {"YES"}: return "Yes."
            if token_set == {"NO"}: return "No."
            if token_set == {"GOOD"}: return "Good."
            if token_set == {"OKAY"}: return "Okay."
            if token_set == {"SORRY"}: return "Sorry."
            if token_set == {"THANKS"}: return "Thank you."
            if token_set == {"GOODBYE"}: return "Goodbye!"
            if token_set == {"HELLO"}: return "Hello!"
            if token_set == {"YES", "GOOD"}: return "Yes, good."
            if token_set == {"THANK", "YOU"}: return "Thank you."
            
            # Custom Dataset Fixes
            if token_set == {"WHAT", "NAME"} or token_set == {"WHAT", "YOU", "NAME"}: return "What is your name?"
            if token_set == {"WHERE", "YOU", "FROM"} or token_set == {"WHERE", "FROM"}: return "Where are you from?"
            if token_set == {"YES", "I", "FROM", "HERE"}: return "Yes, I'm from here."
            if token_set == {"HOW", "YOU", "TODAY"}: return "How are you today?"
            if token_set == {"WHO", "ME", "FRIEND"} or token_set == {"WHO", "I","FRIEND"}: return "Who is my friend?"
            if token_set == {"NO", "ME", "FAMILY"} or token_set == {"NO", "I", "FAMILY"}: return "No. My family."
            if token_set == {"I", "LOVE", "ME", "FAMILY"} or token_set == {"I", "LOVE", "FAMILY"}: return "I love my family."
            if token_set == {"WHY", "YOU", "HERE"}: return "Why are you here?"
            if token_set == {"I", "WANT", "EAT"}: return "I want to eat."
            if token_set == {"WHAT", "YOU", "LIKE"}: return "What do you like?"
            if token_set == {"OKAY", "GOOD"}: return "Okay, good."
            if token_set == {"WHAT", "YOU", "UNDERSTAND"}: return "What did you understand?"
            if token_set == {"I", "WANT", "HELP", "YOU"}: return "I want to help you."
            if token_set == {"PLEASE", "THANKS", "NO"}: return "Please, don't say thanks."
            if token_set == {"THANKS", "FRIEND"}: return "Thanks, friend."
            if token_set == {"I", "WANT", "GO", "HOME"}: return "I want to go home."
            if token_set == {"I", "NO", "KNOW"}: return "I do not know."
            if token_set == {"PLEASE", "GO", "ME"}: return "Please go with me."
            if token_set == {"I", "WANT", "SLEEP"}: return "I want to sleep."

        # 3. FINAL FALLBACK (Strict formatting, preserves repeats)
        # We don't filter lead-ins here so that repeated greetings stay repeated
        result = " ".join(processed_toks).lower().capitalize()
        
        if not result.endswith((".", "!", "?")):
            result += "."
            
        return result.replace("..", ".")
    