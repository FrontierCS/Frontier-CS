import os
import math
import re
from collections import Counter, defaultdict
from typing import List, Dict, Any

TOKEN_RE = re.compile(r"[a-z0-9]+")


def choose_available_tier(preferred: str, candidate_models: List[str]) -> str:
    if not candidate_models:
        return preferred
    if preferred in candidate_models:
        return preferred
    order = ["cheap", "mid", "expensive"]
    try:
        pref_index = order.index(preferred)
    except ValueError:
        pref_index = 1  # default to 'mid'
    best_candidate = None
    best_dist = None
    for cm in candidate_models:
        if cm in order:
            dist = abs(order.index(cm) - pref_index)
        else:
            dist = 10
        if best_candidate is None or dist < best_dist:
            best_candidate = cm
            best_dist = dist
    if best_candidate is None:
        best_candidate = candidate_models[0]
    return best_candidate


class NaiveBayesRouter:
    def __init__(self) -> None:
        self.trained: bool = False
        self.classes = ("cheap", "mid", "expensive")
        self.vocab = set()
        self.vocab_size: int = 0
        self.alpha: float = 0.5
        self.token_counts: Dict[str, Dict[str, int]] = {}
        self.total_token_counts: Dict[str, int] = {}
        self.class_log_prior: Dict[str, float] = {}
        self.log_denom: Dict[str, float] = {}
        self.eval_default: Dict[str, str] = {}
        self.global_default: str = "cheap"

    def train(self) -> None:
        try:
            import pandas as pd  # type: ignore
        except Exception:
            return

        # Locate reference data
        problem_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(problem_dir, "resources", "reference_data.csv")
        if not os.path.exists(path):
            alt_path = os.path.join("resources", "reference_data.csv")
            if os.path.exists(alt_path):
                path = alt_path
            else:
                return

        # Map routing tiers to concrete models in reference data
        acc_cols = {
            "cheap": "mistralai/mistral-7b-chat",
            "mid": "mistralai/mixtral-8x7b-chat",
            "expensive": "gpt-4-1106-preview",
        }
        cost_cols = {tier: f"{model}|total_cost" for tier, model in acc_cols.items()}

        usecols = ["prompt", "eval_name"] + list(acc_cols.values()) + list(cost_cols.values())
        try:
            df = pd.read_csv(path, usecols=usecols)
        except Exception:
            return

        if df.empty:
            return

        n = len(df)
        prompts = df["prompt"].tolist()
        eval_names = df["eval_name"].tolist()

        cheap_acc = df[acc_cols["cheap"]].tolist()
        cheap_cost = df[cost_cols["cheap"]].tolist()
        mid_acc = df[acc_cols["mid"]].tolist()
        mid_cost = df[cost_cols["mid"]].tolist()
        exp_acc = df[acc_cols["expensive"]].tolist()
        exp_cost = df[cost_cols["expensive"]].tolist()

        lam = 150.0

        labels: List[str] = ["" for _ in range(n)]
        global_token_counts: Counter = Counter()
        eval_label_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {c: 0 for c in self.classes}
        )
        global_label_counts: Dict[str, int] = {c: 0 for c in self.classes}

        for i in range(n):
            a_ch = cheap_acc[i]
            c_ch = cheap_cost[i]
            a_mid = mid_acc[i]
            c_mid = mid_cost[i]
            a_exp = exp_acc[i]
            c_exp = exp_cost[i]

            label = self._best_tier_for_row(a_ch, c_ch, a_mid, c_mid, a_exp, c_exp, lam)
            labels[i] = label
            global_label_counts[label] += 1

            en = eval_names[i]
            en_str = "" if en is None else str(en).lower()
            eval_label_counts[en_str][label] += 1

            prompt = prompts[i]
            tokens = self._tokenize(prompt, en_str)
            global_token_counts.update(tokens)

        # Build vocabulary
        MAX_VOCAB = 50000
        if len(global_token_counts) > MAX_VOCAB:
            vocab = {t for t, _ in global_token_counts.most_common(MAX_VOCAB)}
        else:
            vocab = set(global_token_counts.keys())

        if not vocab:
            return

        self.vocab = vocab
        self.vocab_size = len(vocab)

        token_counts: Dict[str, Dict[str, int]] = {
            c: defaultdict(int) for c in self.classes
        }
        class_counts: Dict[str, int] = {c: 0 for c in self.classes}
        total_token_counts: Dict[str, int] = {c: 0 for c in self.classes}

        for i in range(n):
            label = labels[i]
            class_counts[label] += 1
            en = eval_names[i]
            en_str = "" if en is None else str(en).lower()
            prompt = prompts[i]
            tokens = self._tokenize(prompt, en_str)
            for tok in tokens:
                if tok in self.vocab:
                    token_counts[label][tok] += 1
                    total_token_counts[label] += 1

        total_docs = float(n)
        self.alpha = 0.5
        self.token_counts = {c: dict(token_counts[c]) for c in self.classes}
        self.total_token_counts = total_token_counts
        self.class_log_prior = {}
        self.log_denom = {}

        for c in self.classes:
            c_docs = class_counts.get(c, 0)
            if c_docs <= 0:
                prior = 1e-9
            else:
                prior = c_docs / total_docs
            self.class_log_prior[c] = math.log(prior)

            denom = total_token_counts.get(c, 0) + self.alpha * self.vocab_size
            if denom <= 0:
                denom = 1.0
            self.log_denom[c] = math.log(denom)

        self.eval_default = {}
        for en_str, counts in eval_label_counts.items():
            best_lbl = max(self.classes, key=lambda c: counts.get(c, 0))
            self.eval_default[en_str] = best_lbl

        self.global_default = max(self.classes, key=lambda c: global_label_counts.get(c, 0))
        self.trained = True

    def _safe_float(self, val: Any, default: float) -> float:
        if val is None:
            return default
        try:
            if isinstance(val, str):
                if val.strip() == "":
                    return default
                v = float(val)
            else:
                v = float(val)
        except Exception:
            return default
        if v != v:  # NaN check
            return default
        return v

    def _best_tier_for_row(
        self,
        a_cheap: Any,
        c_cheap: Any,
        a_mid: Any,
        c_mid: Any,
        a_exp: Any,
        c_exp: Any,
        lam: float,
    ) -> str:
        a_cheap = self._safe_float(a_cheap, 0.0)
        a_mid = self._safe_float(a_mid, 0.0)
        a_exp = self._safe_float(a_exp, 0.0)
        c_cheap = self._safe_float(c_cheap, 1e9)
        c_mid = self._safe_float(c_mid, 1e9)
        c_exp = self._safe_float(c_exp, 1e9)

        tier_order = {"cheap": 0, "mid": 1, "expensive": 2}
        candidates = [
            ("cheap", a_cheap, c_cheap),
            ("mid", a_mid, c_mid),
            ("expensive", a_exp, c_exp),
        ]

        best_tier = None
        best_score = None
        best_cost = None

        for tier, acc, cost in candidates:
            score = acc - lam * cost
            if best_tier is None:
                best_tier = tier
                best_score = score
                best_cost = cost
            else:
                if score > best_score:
                    best_tier = tier
                    best_score = score
                    best_cost = cost
                elif score == best_score:
                    if cost < best_cost:
                        best_tier = tier
                        best_score = score
                        best_cost = cost
                    elif cost == best_cost:
                        if tier_order[tier] < tier_order[best_tier]:
                            best_tier = tier
                            best_score = score
                            best_cost = cost
        if best_tier is None:
            return "cheap"
        return best_tier

    def _tokenize(self, text: Any, eval_name_lc: str) -> List[str]:
        tokens: List[str] = []
        if eval_name_lc:
            e = str(eval_name_lc).lower()
            tokens.append("eval_" + e)
            parts = e.replace("/", "-").split("-")
            for p in parts:
                p = p.strip()
                if p and p != e:
                    tokens.append("evalpart_" + p)
        if not isinstance(text, str):
            text = "" if text is None else str(text)
        text_lc = text.lower()
        tokens.extend(TOKEN_RE.findall(text_lc))
        return tokens

    def predict(self, query: str, eval_name: str, candidate_models: List[str]) -> str:
        if not candidate_models:
            candidate_models = list(self.classes)

        en_str = "" if eval_name is None else str(eval_name).lower()
        tokens = self._tokenize(query, en_str)
        if not self.vocab:
            preferred = self.eval_default.get(en_str, self.global_default)
            return choose_available_tier(preferred, candidate_models)

        doc_tokens = [t for t in tokens if t in self.vocab]
        if not doc_tokens:
            preferred = self.eval_default.get(en_str, self.global_default)
            return choose_available_tier(preferred, candidate_models)

        doc_counts = Counter(doc_tokens)
        total_doc_tokens = sum(doc_counts.values())
        scores: Dict[str, float] = {}

        for cls in self.classes:
            score = self.class_log_prior.get(cls, math.log(1e-9)) - total_doc_tokens * self.log_denom.get(
                cls, 0.0
            )
            tok_counts_cls = self.token_counts.get(cls, {})
            alpha = self.alpha
            for tok, count in doc_counts.items():
                ctc = tok_counts_cls.get(tok, 0)
                score += count * math.log(ctc + alpha)
            scores[cls] = score

        preferred = max(scores, key=scores.get)
        return choose_available_tier(preferred, candidate_models)


class SimpleHeuristicRouter:
    def predict(self, query: str, eval_name: str, candidate_models: List[str]) -> str:
        if not candidate_models:
            candidate_models = ["cheap", "mid", "expensive"]

        q = "" if query is None else str(query)
        ql = q.lower()
        e = "" if eval_name is None else str(eval_name).lower()
        length = len(ql)

        preferred = "mid"

        hard_eval_markers = (
            "mbpp",
            "humaneval",
            "codeforces",
            "leetcode",
            "aime",
            "math",
            "gsm8k",
            "competition-math",
            "mathqa",
            "openbookqa",
        )
        if any(k in e for k in hard_eval_markers):
            preferred = "expensive"

        hard_text_markers = (
            "python",
            "java",
            "c++",
            "c#",
            "write a function",
            "implement a function",
            "bug",
            "debug",
            "algorithm",
            "time complexity",
            "big-o",
            "sql",
            "regex",
            "dynamic programming",
            "dp problem",
            "code snippet",
            "unit test",
        )
        if any(k in ql for k in hard_text_markers):
            preferred = "expensive"

        reasoning_markers = (
            "prove that",
            "show that",
            "lemma",
            "theorem",
            "corollary",
            "induction",
            "integral",
            "derivative",
            "limit as",
            "probability that",
            "expected value",
            "variance",
            "covariance",
        )
        if any(k in ql for k in reasoning_markers):
            preferred = "expensive"

        mc_markers_eval = ("mmlu", "hellaswag", "arc", "winogrande", "sciq")
        mc_markers_text = ("(a)", "(b)", "(c)", "(d)", " a)", " b)", " c)", " d)")
        if any(k in e for k in mc_markers_eval) or any(k in ql for k in mc_markers_text):
            preferred = "cheap"

        if length > 1200:
            preferred = "expensive"
        elif length > 600 and preferred != "expensive":
            preferred = "mid"
        elif length < 200 and preferred == "mid":
            preferred = "cheap"

        return choose_available_tier(preferred, candidate_models)


_GLOBAL_ROUTER: Any = None


def _get_global_router() -> Any:
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        router = NaiveBayesRouter()
        try:
            router.train()
        except Exception:
            router.trained = False
        if router.trained:
            _GLOBAL_ROUTER = router
        else:
            _GLOBAL_ROUTER = SimpleHeuristicRouter()
    return _GLOBAL_ROUTER


class Solution:
    def solve(self, query: str, eval_name: str, candidate_models: List[str]) -> str:
        router = _get_global_router()
        return router.predict(query, eval_name, candidate_models)