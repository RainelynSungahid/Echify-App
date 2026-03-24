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
        
        # Single object (like FRIEND, FAMILY, HOME)
        if len(token_set) == 1 and next(iter(token_set)) in self.objects:
            return next(iter(token_set)).capitalize()

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

        # ── CUSTOM DATASET FIXES ──

        # 1. GOOD MORNING WHAT NAME
        if token_set == {"GOOD", "MORNING", "WHAT", "NAME"}:
            return "Good morning. What is your name?"

        # 2. WHO ME FRIEND
        if token_set == {"WHO", "ME", "FRIEND"}:
            return "Who is my friend?"

        # 3. NO ME FAMILY
        if token_set == {"NO", "ME", "FAMILY"}:
            return "No. My family."

        # 4. YES I LOVE ME FAMILY
        if token_set == {"YES", "I", "LOVE", "ME", "FAMILY"}:
            return "Yes. I love my family."

        # 5. OKAY GOOD
        if token_set == {"OKAY", "GOOD"}:
            return "Okay, good."

        # 6. YES WHAT YOU UNDERSTAND
        if token_set == {"YES", "WHAT", "YOU", "UNDERSTAND"}:
            return "Yes. What did you understand?"

        # 7. I WANT HELP YOU
        if token_set == {"I", "WANT", "HELP", "YOU"}:
            return "I want to help you."

        # 8. PLEASE THANKS NO
        if token_set == {"PLEASE", "THANKS", "NO"}:
            return "Please, don't say thanks."

        # 9. THANKS FRIEND
        if token_set == {"THANKS", "FRIEND"}:
            return "Thanks, friend."

        # 10. I WANT GO HOME
        if token_set == {"I", "WANT", "GO", "HOME"}:
            return "I want to go home."

        # 11. I NO KNOW PLEASE GO ME
        if token_set == {"I", "NO", "KNOW", "PLEASE", "GO", "ME"}:
            return "I do not know. Please go with me."
        
        if "WHAT" in token_set and "NAME" in token_set:
            return "Good morning. What is your name?" if "MORNING" in token_set else "What is your name?"
        # ── FALLBACK: Intelligent construction (ONLY uses signed words) ──
        return self.intelligent_construct(toks, token_set)
 
    # ─────────────────────────────────────────
    # Intelligent Sentence Construction
    # ─────────────────────────────────────────
    def intelligent_construct(self, toks: List[str], token_set: Set[str]) -> str:
        # 1. Phrase Mapping (Good Morning, Good Afternoon)
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

        # 2. Lead-ins (Priority: HELLO first, then others)
        lead_ins = []
        if "HELLO" in processed_toks: lead_ins.append("Hello")
        
        special_leads = {"GOOD MORNING", "GOOD AFTERNOON", "YES", "NO", "SORRY", "PLEASE", "OKAY", "THANKS", "GOODBYE"}
        for t in processed_toks:
            if t in special_leads or t in self.greetings:
                if t != "HELLO" and t.title() not in lead_ins:
                    lead_ins.append(t.title())
        
        # 3. Core Content
        core_toks = [t for t in processed_toks if t not in special_leads 
                     and t not in self.greetings and t != "HELLO"]
        
        # 4. Clause Splitting (e.g., HELP ME | WANT GO HOME)
        clauses = []
        current_clause = []
        for t in core_toks:
            # Split if we see a new primary action or a question word
            if current_clause and (t in {"HELP", "WANT", "GO", "UNDERSTAND"} or t in self.questions):
                if any(v in self.verbs or v in self.questions for v in current_clause):
                    clauses.append(current_clause)
                    current_clause = []
            current_clause.append(t)
        if current_clause: clauses.append(current_clause)

        # 5. Process Clauses
        final_sentences = []
        for clause in clauses:
            q_word = next((t for t in clause if t in self.questions), None)
            subj = next((t for t in clause if t in self.subjects), None)
            if subj == "ME": subj = "I" # Treat ME as I in subject position
            
            # Verb Priority (LIKE, WANT, UNDERSTAND before EAT, GO)
            raw_verbs = [t for t in clause if t in self.verbs]
            priority = {"LIKE", "WANT", "LOVE", "NEED", "UNDERSTAND", "KNOW"}
            v_list = [v for v in raw_verbs if v in priority] + [v for v in raw_verbs if v not in priority]
            
            objs = [t for t in clause if t not in self.subjects and t not in self.verbs and t not in self.questions]
            
            # NEGATION CHECK: If "NO" was in lead-ins and we have "KNOW" or "UNDERSTAND"
            is_negated = "NO" in token_set and any(v in {"KNOW", "UNDERSTAND"} for v in v_list)

            clause_str = ""
            # A. HELP Request
            if "HELP" in clause:
                clause_str = "can you help me"
            # B. Question Word Present
            elif q_word:
                q_parts = [q_word.title()]
                conn = "do" if v_list else ("are" if subj == "YOU" else "is")
                if subj: q_parts.extend([conn, subj.lower()])
                if v_list:
                    v_str = v_list[0].lower()
                    if len(v_list) > 1: v_str += f" to {' and '.join([v.lower() for v in v_list[1:]])}"
                    q_parts.append(v_str)
                q_parts.extend([o.lower() for o in objs])
                clause_str = " ".join(q_parts)
            # C. Standard Statement
            else:
                parts = []
                # Use "I'm" for "I GOOD" or "I GO EAT"
                if subj == "I" and (not v_list or "GO" in v_list):
                    parts.append("I'm")
                elif subj:
                    parts.append(subj.title() if subj != "I" else "I")
                elif not subj and v_list: parts.append("I") # Default subject
                
                if v_list:
                    main_v = v_list[0].lower()
                    if is_negated: main_v = f"do not {main_v}"
                    
                    if "GO" in v_list and len(v_list) > 1:
                        others = [v.lower() for v in v_list if v != "GO"]
                        parts.append(f"going to {' and '.join(others)}")
                    else:
                        main_v_conj = self._conjugate_verb(v_list[0], subj if subj else "I")
                        if is_negated: main_v_conj = f"do not {v_list[0].lower()}"
                        if len(v_list) > 1:
                            parts.append(f"{main_v_conj} to {' and '.join([v.lower() for v in v_list[1:]])}")
                        else: parts.append(main_v_conj)
                
                parts.extend([o.lower() for o in objs])
                clause_str = " ".join(parts)

            # Punctuation
            punc = "?" if (q_word or "HELP" in clause) else "."
            final_sentences.append(clause_str.strip().capitalize() + punc)

        # 6. Final Construction
        lead_str = ", ".join(lead_ins)
        if lead_str:
            # If lead-ins exist, add them as a separate introductory sentence/phrase
            lead_str += "."
            
        return (lead_str + " " + " ".join(final_sentences)).strip().replace("..", ".")
    
    def _conjugate_verb(self, verb: str, subject: str) -> str:
        """Conjugate verb based on subject with support for continuous 'ing' for certain actions"""
        # If we are using the "I'm" contraction (handled in intelligent_construct), 
        # some verbs sound better as gerunds.
        use_ing = (subject == "I")
        
        mapping = {
            "WANT": "want" if subject == "I" else "wants",
            "LOVE": "love" if subject == "I" else "loves",
            "LIKE": "like" if subject == "I" else "likes",
            "NEED": "need" if subject == "I" else "needs",
            "KNOW": "know" if subject == "I" else "knows",
            "UNDERSTAND": "understand" if subject == "I" else "understands",
            "EAT": "eating" if use_ing else ("eat" if subject == "I" else "eats"),
            "SLEEP": "sleeping" if use_ing else ("sleep" if subject == "I" else "sleeps"),
            "GO": "going" if use_ing else ("go" if subject == "I" else "goes"),
            "HELP": "helping" if use_ing else ("help" if subject == "I" else "helps"),
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