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
        if self.tokens and self.tokens[-1] == token:
            self.last_token_time = now
            return None

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
        
        # Create token set for easy checking
        token_set = set(toks)
        
        # ── EXACT PATTERN MATCHING ──
        # These patterns ONLY match if the signed words are EXACTLY these (order doesn't matter)
        
        # Single word responses
        if token_set == {"YES"}:
            return "Yes."
        if token_set == {"NO"}:
            return "No."
        if token_set == {"GOOD"}:
            return "Good."
        if token_set == {"OKAY"}:
            return "Okay."
        if token_set == {"SORRY"}:
            return "Sorry."
        if token_set == {"THANKS"}:
            return "Thanks."
        if token_set == {"GOODBYE"}:
            return "Goodbye!"
        if token_set == {"HELLO"}:
            return "Hello!"
        
        # Two word combinations
        if token_set == {"YES", "GOOD"}:
            return "Yes, good."
        if token_set == {"GOOD", "MORNING"}:
            return "Good morning!"
        if token_set == {"THANK", "YOU"}:
            return "Thank you."
        
        # Eating patterns (EXACT matches only)
        if token_set == {"YES", "PLEASE", "I", "WANT", "EAT"}:
            return "Yes, please. I want to eat."
        if token_set == {"I", "WANT", "EAT", "PLEASE"}:
            return "Please, I want to eat."
        if token_set == {"I", "WANT", "EAT"}:
            return "I want to eat."
        if token_set == {"SORRY", "WHERE", "EAT"}:
            return "Sorry, where can I eat?"
        if token_set == {"WHERE", "EAT"}:
            return "Where can I eat?"
        
        # Help patterns
        if token_set == {"YES", "PLEASE", "YOU", "GO", "ME", "HOME"}:
            return "Yes, please help me go home."
        if token_set == {"YOU", "GO", "ME", "HOME"}:
            return "Please help me go home."
        if token_set == {"HELP", "ME"}:
            return "Help me."
        if token_set == {"PLEASE", "HELP", "ME"}:
            return "Please help me."
        
        # Family/love patterns
        if token_set == {"I", "LOVE", "FAMILY"}:
            return "I love my family."
        if token_set == {"YES", "I", "LOVE", "FAMILY"}:
            return "Yes, I love my family."
        
        # Sleep patterns
        if token_set == {"I", "WANT", "SLEEP"}:
            return "I want to sleep."
        if token_set == {"YES", "I", "WANT", "SLEEP"}:
            return "Yes, I want to sleep."
        
        # Location patterns
        if token_set == {"I", "FROM", "HERE"}:
            return "I'm from here."
        if token_set == {"WHERE", "HOME"}:
            return "Where is my home?"
        
        # Goodbye patterns
        if token_set == {"LOVE", "YOU", "GOODBYE"}:
            return "I love you. Goodbye!"
        
        # ── FALLBACK: Intelligent construction (ONLY uses signed words) ──
        return self.intelligent_construct(toks, token_set)
 
    # ─────────────────────────────────────────
    # Intelligent Sentence Construction
    # ─────────────────────────────────────────
    def intelligent_construct(self, toks: List[str], token_set: Set[str]) -> str:
        """
        Preserves greetings and constructs sentences using ONLY signed words.
        """
        # 1. Identify "Lead-in" words (Greetings/Interjections)
        lead_ins = [t.capitalize() for t in toks if t in self.greetings or t in {"YES", "NO", "SORRY", "PLEASE"}]
        
        # 2. Filter out what we've already used for the lead-in to find the "core" message
        remaining_toks = [t for t in toks if t not in self.greetings and t not in {"YES", "NO", "SORRY", "PLEASE"}]
        
        subject = None
        verbs = []
        others = []

        for t in remaining_toks:
            if t in self.subjects:
                subject = "I" if t in {"I", "ME"} else t.lower()
            elif t in self.verbs:
                verbs.append(t)
            else:
                others.append(t.lower())

        # 3. Build the core sentence
        core_parts = []
        if subject:
            core_parts.append(subject)
            # Special case: If I + Adjective (no verb signed), add "'m" or "am"
            if not verbs and others:
                if subject == "I":
                    core_parts[-1] = "I'm"
                else:
                    core_parts.append("is")
        
        if verbs:
            # Handle "WANT EAT" -> "want to eat"
            conjugated = [self._conjugate_verb(v, subject if subject else "I") for v in verbs]
            if len(conjugated) > 1 and verbs[0] in {"WANT", "LIKE", "NEED"}:
                core_parts.append(f"{conjugated[0]} to {' and '.join(verbs[1:]).lower()}")
            else:
                core_parts.append(" and ".join(conjugated))

        core_parts.extend(others)

        # 4. Combine Lead-ins with Core
        lead_str = ", ".join(lead_ins)
        core_str = " ".join(core_parts)

        if lead_str and core_str:
            final = f"{lead_str}, {core_str}."
        elif lead_str:
            final = f"{lead_str}."
        elif core_str:
            final = f"{core_str.capitalize()}."
        else:
            final = " ".join(toks).lower().capitalize() + "."

        return final
    
    def _conjugate_verb(self, verb: str, subject: str) -> str:
        """Conjugate verb based on subject"""
        mapping = {
            "WANT": "want" if subject == "I" else "wants",
            "LOVE": "love" if subject == "I" else "loves",
            "LIKE": "like" if subject == "I" else "likes",
            "NEED": "need" if subject == "I" else "needs",
            "KNOW": "know" if subject == "I" else "knows",
            "UNDERSTAND": "understand" if subject == "I" else "understands",
            "GO": "go" if subject == "I" else "goes",
            "EAT": "eat" if subject == "I" else "eats",
            "SLEEP": "sleep" if subject == "I" else "sleeps",
            "HELP": "help" if subject == "I" else "helps",
        }
        return mapping.get(verb, verb.lower())
    
    def _to_gerund(self, verb: str) -> str:
        """Convert verb to gerund (-ing form)"""
        gerund_map = {
            "EAT": "eating",
            "SLEEP": "sleeping",
            "GO": "going",
            "HELP": "helping",
            "LIKE": "liking",
            "LOVE": "loving",
        }
        return gerund_map.get(verb, verb.lower() + "ing")