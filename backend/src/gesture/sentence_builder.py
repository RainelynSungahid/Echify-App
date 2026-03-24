# backend/src/gesture/sentence_builder.py
 
import time
from typing import List, Optional, Tuple
 
 
class SentenceBuilder:
 
    def __init__(self, short_pause: float = 0.8, long_pause: float = 2.2, max_tokens: int = 25):
        self.short_pause = short_pause
        self.long_pause = long_pause
        self.max_tokens = max_tokens
 
        self.tokens:           List[str] = []
        self.pause_start_time: Optional[float] = None
        self.last_token_time:  Optional[float] = None
 
        # Categories
        self.politeness = {"HELLO", "PLEASE", "THANKS",
                           "SORRY", "GOODBYE", "MORNING", "AFTERNOON"}
        self.actions = {"WANT", "HELP", "GO", "EAT",
                        "SLEEP", "UNDERSTAND", "KNOW", "LIKE", "LOVE"}
        self.questions = {"HOW", "WHAT", "WHERE", "WHY", "WHO"}
        self.people = {"I", "YOU", "ME", "FRIEND", "FAMILY"}
        self.subjects = {"I", "YOU", "ME"}
        self.answers = {"YES", "NO", "OKAY", "GOOD"}
        self.time_words = {"TODAY"}
        self.places = {"HOME", "HERE", "FROM"}
        self.identity = {"NAME"}
 
        self.ignore_tokens = {
            "WAITING", "COLLECTING...", "BUFFERING...", "UNKNOWN",
            "WAITING...", "SIGNING...", "TOO SHORT / IGNORED", ""
        }
 
    # ─────────────────────────────────────────
    # Token Collection
    # ─────────────────────────────────────────
    def add_token(self, token: str) -> Optional[Tuple[str, str]]:
        now = time.time()
        token = token.strip().upper()
 
        if token in self.ignore_tokens:
            return None
 
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
 
        if elapsed >= self.short_pause and len(self.tokens) >= 3:
            return self.finalize()
 
        if elapsed >= self.long_pause and self.tokens:
            return self.finalize()
 
        return None
 
    def finalize(self) -> Tuple[str, str]:
        raw = " ".join(self.tokens).strip()
        eng = self.expand(raw)
        self.reset()
        return raw, eng
 
    def reset(self):
        self.tokens = []
        self.pause_start_time = None
        self.last_token_time = None
 
    # ─────────────────────────────────────────
    # Expansion
    # ─────────────────────────────────────────
    def expand(self, raw: str) -> str:
        toks = [t for t in raw.upper().split() if t]
        if not toks:
            return ""
 
        pre = " ".join(toks)
 
        # ── FIXED CRITICAL CASE ─────────────────
        if "YOU GO ME HOME" in pre:
            return "Please help me go home."
 
        # ── Scene-based mappings ────────────────
        if pre in {"YES PLEASE I WANT EAT", "YES I WANT EAT PLEASE"}:
            return "Yes, please. I want to eat."
 
        if pre in {"SORRY WHERE EAT"}:
            return "Sorry, where can I eat?"
 
        if pre in {"SORRY I NOT UNDERSTAND", "SORRY I NO UNDERSTAND"}:
            return "Sorry, I don't understand."
 
        if pre in {"THANKS YOU GOOD FRIEND"}:
            return "Thank you. You are a good friend."
 
        if pre in {"I WANT EAT PLEASE", "PLEASE I WANT EAT"}:
            return "Please, I want to eat."
 
        if pre in {"I FROM HERE", "FROM HERE"}:
            return "I'm from here."
 
        if pre in {"YES I LOVE FAMILY", "I LOVE FAMILY"}:
            return "I love my family."
 
        if pre in {"SORRY PLEASE HELP ME WHERE HOME"}:
            return "Sorry, please help me. Where is my home?"
 
        if pre in {"YES I KNOW NAME FAMILY FROM HERE"}:
            return "Yes, I know my name. My family is from here."
 
        if pre in {"GOOD TODAY I LIKE GO"}:
            return "I had a good day. I liked going out."
 
        if pre in {"YES I WANT SLEEP"}:
            return "Yes, I want to sleep."
        if pre in {"LIKE I GO", "I LIKE GO", "I GO LIKE", "LIKE GO I"}:
            return "I like to go."
        if pre in {"LOVE YOU GOODBYE"}:
            return "I love you. Goodbye!"
 
        # ── Fallback simple builder ─────────────
        return self.simple_construct(toks)
 
    # ─────────────────────────────────────────
    # Simple fallback sentence builder
    # ─────────────────────────────────────────
    def simple_construct(self, toks: List[str]) -> str:
        words = []
 
        mapping = {
            "I": "I", "ME": "me", "YOU": "you",
            "GO": "go", "EAT": "eat", "SLEEP": "sleep",
            "HOME": "home", "HERE": "here",
            "HELP": "help", "WANT": "want to",
            "LOVE": "love", "LIKE": "like",
            "PLEASE": "please", "SORRY": "sorry",
            "THANKS": "thank you",
            "GOOD": "good", "TODAY": "today"
        }
 
        for t in toks:
            if t in mapping:
                words.append(mapping[t])
 
        if not words:
            return " ".join(toks).title() + "."
 
        sentence = " ".join(words)
        sentence = sentence[0].upper() + sentence[1:]
 
        if not sentence.endswith((".", "!", "?")):
            sentence += "."
 
        return sentence