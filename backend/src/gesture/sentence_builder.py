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

        self.question_words = {"HOW", "WHAT", "WHERE", "WHY", "WHO"}
        self.subject_words = {"I", "ME", "YOU"}
        self.verb_words = {
            "WANT", "HELP", "GO", "EAT", "SLEEP",
            "UNDERSTAND", "KNOW", "LIKE", "LOVE", "NEED"
        }

        self.standalone_phrases = {
            "HELLO", "GOODBYE", "THANKS", "SORRY",
            "YES", "NO", "OKAY", "GOOD",
            "GOOD MORNING", "GOOD AFTERNOON"
        }

        self.ignore_tokens = {
            "WAITING", "COLLECTING...", "BUFFERING...", "UNKNOWN",
            "WAITING...", "SIGNING...", "TOO SHORT / IGNORED",
            "", "COLLECTING..."
        }

        self.word_map = {
            "HELLO": "hello",
            "GOODBYE": "goodbye",
            "THANKS": "thank you",
            "SORRY": "sorry",
            "YES": "yes",
            "NO": "no",
            "OKAY": "okay",
            "GOOD": "good",
            "BAD": "bad",
            "I": "I",
            "ME": "me",
            "YOU": "you",
            "WANT": "want",
            "HELP": "help",
            "GO": "go",
            "EAT": "eat",
            "SLEEP": "sleep",
            "UNDERSTAND": "understand",
            "KNOW": "know",
            "LIKE": "like",
            "LOVE": "love",
            "NEED": "need",
            "HOME": "home",
            "FAMILY": "family",
            "FRIEND": "friend",
            "NAME": "name",
            "FOOD": "food",
            "HERE": "here",
            "FROM": "from",
            "TODAY": "today",
            "WHAT": "what",
            "WHERE": "where",
            "WHY": "why",
            "WHO": "who",
            "HOW": "how",
            "PLEASE": "please",
            "GOOD MORNING": "good morning",
            "GOOD AFTERNOON": "good afternoon",
        }

    # ------------------------------------------------------------
    # Token collection
    # ------------------------------------------------------------
    def add_token(self, token: str) -> Optional[Tuple[str, str]]:
        now = time.time()
        token = token.strip().upper()

        if token in self.ignore_tokens:
            return None

        # Allows repeated words like HELLO HELLO HELLO
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

        if now - self.pause_start_time >= self.long_pause and self.tokens:
            return self.finalize()

        return None

    def finalize(self) -> Tuple[str, str]:
        raw = " ".join(self.tokens).strip()
        eng = self.expand(raw)

        self.tokens = []
        self.pause_start_time = None
        self.last_token_time = None

        return raw, eng

    def reset(self):
        self.tokens = []
        self.pause_start_time = None
        self.last_token_time = None

    # ------------------------------------------------------------
    # Main expansion
    # ------------------------------------------------------------
    def expand(self, raw: str) -> str:
        toks = [t for t in raw.upper().split() if t]
        if not toks:
            return ""

        toks = self._merge_phrases(toks)
        chunks = self._split_into_chunks(toks)

        rendered = []
        for i, chunk in enumerate(chunks):
            out = self._render_single_chunk(
                chunk, is_last=(i == len(chunks) - 1))
            if out:
                rendered.append(out)

        return " ".join(rendered) if rendered else self._literal_render(toks)

    def _merge_phrases(self, toks: List[str]) -> List[str]:
        merged = []
        i = 0

        while i < len(toks):
            if toks[i] == "GOOD" and i + 1 < len(toks) and toks[i + 1] in {"MORNING", "AFTERNOON"}:
                merged.append(f"GOOD {toks[i + 1]}")
                i += 2
            else:
                merged.append(toks[i])
                i += 1

        return merged

    # ------------------------------------------------------------
    # Chunk splitting
    # ------------------------------------------------------------
    def _split_into_chunks(self, toks: List[str]) -> List[List[str]]:
        if not toks:
            return []

        chunks: List[List[str]] = []
        current: List[str] = []

        for tok in toks:
            if not current:
                current.append(tok)
                continue

            if self._should_start_new_chunk(current, tok):
                chunks.append(current)
                current = [tok]
            else:
                current.append(tok)

        if current:
            chunks.append(current)

        return self._postprocess_chunks(chunks)

    def _should_start_new_chunk(self, current: List[str], tok: str) -> bool:
        starters = {
            "PLEASE", "HELLO", "GOODBYE", "THANKS", "SORRY",
            "YES", "NO", "OKAY", "GOOD", "GOOD MORNING", "GOOD AFTERNOON"
        }

        if tok in self.question_words and self._chunk_has_meaning(current):
            return True

        if tok in starters and self._chunk_has_meaning(current):
            return True

        return False

    def _chunk_has_meaning(self, chunk: List[str]) -> bool:
        if not chunk:
            return False

        token_set = set(chunk)

        if len(chunk) == 1 and chunk[0] in self.standalone_phrases:
            return True

        if chunk[0] in self.question_words and len(chunk) >= 2:
            return True

        known_patterns = [
            {"I", "NO", "KNOW"},
            {"NO", "KNOW"},
            {"I", "FROM", "HERE"},
            {"YES", "I", "FROM", "HERE"},
            {"PLEASE", "GO", "ME"},
            {"GO", "ME"},
            {"I", "LOVE", "YOU"},
            {"LOVE", "YOU"},
            {"I", "LOVE", "FAMILY"},
            {"I", "LOVE", "ME", "FAMILY"},
            {"LOVE", "FAMILY"},
            {"LOVE", "ME", "FAMILY"},
            {"ME", "NAME"},
            {"I", "WANT", "HELP"},
            {"WANT", "HELP"},
            {"I", "WANT", "HELP", "YOU"},
            {"WANT", "HELP", "YOU"},
            {"HELP", "YOU"},
            {"I", "WANT", "SLEEP"},
            {"WANT", "SLEEP"},
            {"I", "WANT", "EAT"},
            {"WANT", "EAT"},
            {"I", "WANT", "GO", "HOME"},
            {"WANT", "GO", "HOME"},
            {"GO", "HOME"},
        ]

        if token_set in known_patterns:
            return True

        return len(chunk) >= 3

    def _postprocess_chunks(self, chunks: List[List[str]]) -> List[List[str]]:
        if not chunks:
            return []

        merged: List[List[str]] = []

        for chunk in chunks:
            if not merged:
                merged.append(chunk)
                continue

            if self._is_weak_chunk(chunk):
                merged[-1].extend(chunk)
            else:
                merged.append(chunk)

        return merged

    def _is_weak_chunk(self, chunk: List[str]) -> bool:
        return (
            bool(chunk)
            and len(chunk) == 1
            and chunk[0] not in self.standalone_phrases
            and chunk[0] not in self.question_words
        )

    # ------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------
    def _render_single_chunk(self, chunk: List[str], is_last: bool = False) -> str:
        exact = self._render_exact(chunk, is_last=is_last)
        if exact:
            return exact

        fuzzy = self._render_fuzzy(chunk)
        if fuzzy:
            return fuzzy

        return self._grammar_fallback_strict(chunk, is_last=is_last)

    def _render_exact(self, chunk: List[str], is_last: bool = False) -> Optional[str]:
        token_set = set(chunk)

        # Repeated standalone words
        if all(tok == "HELLO" for tok in chunk):
            return " ".join(["Hello!"] * len(chunk))
        if all(tok == "GOODBYE" for tok in chunk):
            return " ".join(["Goodbye!"] * len(chunk))
        if all(tok == "THANKS" for tok in chunk):
            return " ".join(["Thank you."] * len(chunk))
        if all(tok == "SORRY" for tok in chunk):
            return " ".join(["Sorry."] * len(chunk))
        if all(tok == "YES" for tok in chunk):
            return " ".join(["Yes."] * len(chunk))
        if all(tok == "NO" for tok in chunk):
            return " ".join(["No."] * len(chunk))
        if all(tok == "OKAY" for tok in chunk):
            return " ".join(["Okay."] * len(chunk))
        if all(tok == "GOOD" for tok in chunk):
            return " ".join(["Good."] * len(chunk))

        # Standalone
        if chunk == ["GOOD MORNING"]:
            return "Good morning!"
        if chunk == ["GOOD AFTERNOON"]:
            return "Good afternoon!"

        # Questions
        if token_set == {"WHAT", "NAME"} or token_set == {"WHAT", "YOU", "NAME"}:
            return "What is your name?"
        if token_set == {"WHERE", "FROM"} or token_set == {"WHERE", "YOU", "FROM"}:
            return "Where are you from?"
        if token_set == {"WHY", "HERE"} or token_set == {"WHY", "YOU", "HERE"}:
            return "Why are you here?"
        if token_set == {"HOW", "YOU"}:
            return "How are you?"
        if token_set == {"HOW", "YOU", "TODAY"} or token_set == {"HOW", "TODAY"}:
            return "How are you today?"
        if token_set == {"WHAT", "LIKE"} or token_set == {"WHAT", "YOU", "LIKE"}:
            return "What do you like?"
        if token_set == {"WHAT", "UNDERSTAND"} or token_set == {"WHAT", "YOU", "UNDERSTAND"}:
            return "What did you understand?"

        # ME -> MY cases
        if token_set == {"ME", "NAME"}:
            return "My name."
        if token_set == {"I", "LOVE", "ME", "FAMILY"}:
            return "I love my family."
        if token_set == {"LOVE", "ME", "FAMILY"}:
            return "Love my family."

        # Statements
        if token_set == {"I", "NO", "KNOW"}:
            return "I do not know."
        if token_set == {"NO", "KNOW"}:
            return "Do not know."

        if token_set == {"PLEASE", "GO", "ME"}:
            return "Please go with me."
        if token_set == {"GO", "ME"}:
            return "Go with me."

        if token_set == {"I", "LOVE", "YOU"}:
            return "I love you."
        if token_set == {"LOVE", "YOU"}:
            return "Love you."

        if token_set == {"I", "LOVE", "FAMILY"}:
            return "I love my family."
        if token_set == {"LOVE", "FAMILY"}:
            return "Love family."

        if token_set == {"I", "WANT", "HELP"}:
            return "I want help."
        if token_set == {"WANT", "HELP"}:
            return "Want help."
        if token_set == {"I", "WANT", "HELP", "YOU"}:
            return "I want to help you."
        if token_set == {"WANT", "HELP", "YOU"}:
            return "Want to help you."
        if token_set == {"HELP", "YOU"}:
            return "Help you."

        if token_set == {"I", "WANT", "SLEEP"}:
            return "I want to sleep."
        if token_set == {"WANT", "SLEEP"}:
            return "Want to sleep."

        if token_set == {"I", "WANT", "EAT"}:
            return "I want to eat."
        if token_set == {"WANT", "EAT"}:
            return "Want to eat."

        if token_set == {"I", "WANT", "GO", "HOME"}:
            return "I want to go home."
        if token_set == {"WANT", "GO", "HOME"}:
            return "Want to go home."
        if token_set == {"GO", "HOME"}:
            return "Go home."

        # YES-prefixed statements
        if token_set == {"YES", "I", "WANT", "SLEEP"}:
            return "Yes. I want to sleep."
        if token_set == {"YES", "WANT", "SLEEP"}:
            return "Yes. Want to sleep."
        if token_set == {"YES", "I", "WANT", "EAT"}:
            return "Yes. I want to eat."
        if token_set == {"YES", "WANT", "EAT"}:
            return "Yes. Want to eat."
        if token_set == {"YES", "I", "WANT", "GO", "HOME"}:
            return "Yes. I want to go home."
        if token_set == {"YES", "WANT", "GO", "HOME"}:
            return "Yes. Want to go home."
        if token_set == {"YES", "I", "WANT", "HELP"}:
            return "Yes. I want help."
        if token_set == {"YES", "WANT", "HELP"}:
            return "Yes. Want help."
        if token_set == {"YES", "I", "WANT", "HELP", "YOU"}:
            return "Yes. I want to help you."
        if token_set == {"YES", "WANT", "HELP", "YOU"}:
            return "Yes. Want to help you."
        if token_set == {"YES", "I", "LOVE", "ME", "FAMILY"}:
            return "Yes. I love my family."
        if token_set == {"YES", "I", "FROM", "HERE"}:
            return "Yes, I'm from here."
        if token_set == {"I", "FROM", "HERE"}:
            return "I'm from here."

        return None

    def _render_fuzzy(self, chunk: List[str]) -> Optional[str]:
        token_set = set(chunk)

        candidates = [
            ({"WHAT", "YOU", "NAME"}, "What is your name?"),
            ({"WHAT", "NAME"}, "What is your name?"),
            ({"WHERE", "YOU", "FROM"}, "Where are you from?"),
            ({"WHERE", "FROM"}, "Where are you from?"),
            ({"WHY", "YOU", "HERE"}, "Why are you here?"),
            ({"WHY", "HERE"}, "Why are you here?"),
            ({"WHO", "ME", "FRIEND"}, "Who is my friend?"),
            ({"HOW", "YOU", "TODAY"}, "How are you today?"),
            ({"HOW", "YOU"}, "How are you?"),
            ({"ME", "NAME"}, "My name."),
            ({"I", "LOVE", "ME", "FAMILY"}, "I love my family."),
            ({"LOVE", "ME", "FAMILY"}, "Love my family."),
            ({"I", "NO", "KNOW"}, "I do not know."),
            ({"NO", "KNOW"}, "Do not know."),
            ({"PLEASE", "GO", "ME"}, "Please go with me."),
            ({"GO", "ME"}, "Go with me."),
            ({"I", "LOVE", "YOU"}, "I love you."),
            ({"LOVE", "YOU"}, "Love you."),
            ({"I", "LOVE", "FAMILY"}, "I love my family."),
            ({"LOVE", "FAMILY"}, "Love family."),
            ({"I", "WANT", "HELP"}, "I want help."),
            ({"WANT", "HELP"}, "Want help."),
            ({"I", "WANT", "HELP", "YOU"}, "I want to help you."),
            ({"WANT", "HELP", "YOU"}, "Want to help you."),
            ({"HELP", "YOU"}, "Help you."),
            ({"I", "WANT", "SLEEP"}, "I want to sleep."),
            ({"WANT", "SLEEP"}, "Want to sleep."),
            ({"I", "WANT", "EAT"}, "I want to eat."),
            ({"WANT", "EAT"}, "Want to eat."),
            ({"I", "WANT", "GO", "HOME"}, "I want to go home."),
            ({"WANT", "GO", "HOME"}, "Want to go home."),
            ({"GO", "HOME"}, "Go home."),
        ]

        best_output = None
        best_score = 0.0

        for expected_set, output in candidates:
            score = self._grammar_similarity_score(
                token_set, expected_set, output)
            if score > best_score:
                best_score = score
                best_output = output

        return best_output if best_score >= 0.72 else None

    def _grammar_similarity_score(self, chunk_set: Set[str], expected_set: Set[str], output: str) -> float:
        intersection = len(chunk_set & expected_set)
        union = len(chunk_set | expected_set)
        jaccard = intersection / union if union else 0.0
        size_penalty = abs(len(chunk_set) - len(expected_set)) * 0.08
        score = jaccard - size_penalty

        if "YES" in chunk_set and output.startswith("Yes"):
            score += 0.10
        if "PLEASE" in chunk_set and "please" in output.lower():
            score += 0.10
        if "LOVE" in chunk_set and "love" in output.lower():
            score += 0.08
        if "WANT" in chunk_set and "want" in output.lower():
            score += 0.08
        if "ME" in chunk_set and "my" in output.lower():
            score += 0.08

        return score

    # ------------------------------------------------------------
    # Strict grammar fallback
    # ------------------------------------------------------------
    def _grammar_fallback_strict(self, chunk: List[str], is_last: bool = False) -> str:
        if not chunk:
            return ""

        if chunk[0] in self.question_words:
            transformed = self._reorder_without_adding_dataset_words(chunk)
            text = " ".join(transformed).capitalize()
            return text + "?"

        token_set = set(chunk)
        yes_prefix = "YES" in token_set
        please_prefix = "PLEASE" in token_set

        working = [tok for tok in chunk if tok not in {"YES", "PLEASE"}]
        transformed = self._reorder_without_adding_dataset_words(working)

        text = " ".join(transformed).strip()
        if text:
            text = text[0].upper() + text[1:]

        if yes_prefix:
            text = f"Yes. {text}" if text else "Yes."
        if please_prefix:
            text = f"Please {text[0].lower() + text[1:]}" if text else "Please."

        if chunk[-1] == "OKAY":
            core = text.replace(" okay", "").replace(" Okay", "").strip()
            if core and not core.endswith((".", "!", "?")):
                core += "."
            return f"{core} Okay?"

        if not text.endswith((".", "!", "?")):
            text += "."

        return text

    def _reorder_without_adding_dataset_words(self, chunk: List[str]) -> List[str]:
        if not chunk:
            return []

        token_set = set(chunk)

        # Specific safe transforms
        if token_set == {"LOVE", "YOU"}:
            return ["love", "you"]
        if token_set == {"I", "LOVE", "YOU"} or chunk == ["LOVE", "I", "YOU"]:
            return ["I", "love", "you"]

        if token_set == {"NO", "KNOW"}:
            return ["do", "not", "know"]
        if token_set == {"I", "NO", "KNOW"}:
            return ["I", "do", "not", "know"]

        if token_set == {"GO", "ME"}:
            return ["go", "with", "me"]

        if token_set == {"WANT", "SLEEP"}:
            return ["want", "to", "sleep"]
        if token_set == {"I", "WANT", "SLEEP"}:
            return ["I", "want", "to", "sleep"]

        if token_set == {"WANT", "EAT"}:
            return ["want", "to", "eat"]
        if token_set == {"I", "WANT", "EAT"}:
            return ["I", "want", "to", "eat"]

        if token_set == {"WANT", "GO", "HOME"}:
            return ["want", "to", "go", "home"]
        if token_set == {"I", "WANT", "GO", "HOME"}:
            return ["I", "want", "to", "go", "home"]

        if token_set == {"WANT", "HELP"}:
            return ["want", "help"]
        if token_set == {"I", "WANT", "HELP"}:
            return ["I", "want", "help"]
        if token_set == {"HELP", "YOU"}:
            return ["help", "you"]
        if token_set == {"WANT", "HELP", "YOU"}:
            return ["want", "to", "help", "you"]
        if token_set == {"I", "WANT", "HELP", "YOU"}:
            return ["I", "want", "to", "help", "you"]

        # General subject-verb-object reorder
        subject = None
        verb = None
        remainder = []

        for tok in chunk:
            if subject is None and tok in {"I", "YOU", "ME"}:
                subject = self.word_map.get(tok, tok.lower())
            elif verb is None and tok in self.verb_words:
                verb = self.word_map.get(tok, tok.lower())
            else:
                remainder.append(self.word_map.get(tok, tok.lower()))

        if subject and verb:
            if verb == "want" and remainder:
                base = [subject, "want"] + remainder
            else:
                base = [subject, verb] + remainder
        elif verb and remainder:
            if verb == "want":
                base = ["want"] + remainder
            else:
                base = [verb] + remainder
        else:
            base = [self.word_map.get(tok, tok.lower()) for tok in chunk]

        # ME -> MY when before a noun-like word
        converted = []
        for i, word in enumerate(base):
            if word == "me" and i + 1 < len(base):
                next_word = base[i + 1]
                if next_word in {"name", "family", "friend", "home", "food"}:
                    word = "my"
            converted.append(word)

        return converted

    def _literal_render(self, chunk: List[str], force_question: bool = False) -> str:
        words = [self.word_map.get(tok, tok.lower()) for tok in chunk]
        text = " ".join(words).capitalize()
        return text + ("?" if force_question else ".")
