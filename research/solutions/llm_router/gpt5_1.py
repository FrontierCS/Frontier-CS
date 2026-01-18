import os
import re
import ast
import math
import threading
from collections import Counter, defaultdict

import numpy as np
import pandas as pd


# Global constants and mapping
LAMBDA = 150.0
TIERS = ["cheap", "mid", "expensive"]
TIER_TO_MODEL = {
    "cheap": "mistralai/mistral-7b-chat",
    "mid": "mistralai/mixtral-8x7b-chat",
    "expensive": "gpt-4-1106-preview",
}


def _find_data_path():
    candidates = [
        os.path.join("resources", "reference_data.csv"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "reference_data.csv"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "reference_data.csv"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _safe_text_from_prompt(val):
    if val is None:
        return ""
    try:
        s = str(val)
    except Exception:
        return ""
    s_strip = s.strip()
    # Attempt to parse list-like string representations
    if len(s_strip) >= 2 and s_strip[0] == "[" and s_strip[-1] == "]" and ("'" in s_strip or '"' in s_strip):
        try:
            parsed = ast.literal_eval(s_strip)
            if isinstance(parsed, (list, tuple)):
                joined = " ".join([str(x) for x in parsed])
                return joined.replace("\\n", "\n")
        except Exception:
            pass
    return s_strip.replace("\\n", "\n")


class NaiveBayesTextClassifier:
    def __init__(self, class_labels, alpha=1.0, max_vocab=30000, min_token_count=2, per_doc_count_cap=4):
        self.class_labels = list(class_labels)
        self.label_to_idx = {l: i for i, l in enumerate(self.class_labels)}
        self.alpha = float(alpha)
        self.max_vocab = int(max_vocab)
        self.min_token_count = int(min_token_count)
        self.per_doc_count_cap = int(per_doc_count_cap)

        # Filled after fit
        self.vocab = {}
        self.idx_to_token = []
        self.log_likelihood = None  # shape (C, V)
        self.log_prior = None  # shape (C,)
        self.fitted = False

    def _tokenize(self, text, eval_name):
        if text is None:
            text = ""
        # Normalize
        txt = str(text)
        tl = txt.lower()

        tokens = re.findall(r"[a-z0-9_]+", tl)
        # Filter tokens
        filt_tokens = [t for t in tokens if 2 <= len(t) <= 30]

        # Add feature tokens
        feats = []

        if eval_name:
            en = str(eval_name).strip().lower()
            feats.append("eval=" + en)

        char_len = len(tl)
        word_len = len(filt_tokens)

        # Length bins
        char_bins = [80, 180, 360, 700, 1200]
        word_bins = [12, 25, 50, 100, 200]
        cbin = 0
        for b in char_bins:
            if char_len <= b:
                break
            cbin += 1
        wbin = 0
        for b in word_bins:
            if word_len <= b:
                break
            wbin += 1
        feats.append(f"char_bin={cbin}")
        feats.append(f"word_bin={wbin}")

        # Multiple choice pattern
        has_choice = False
        if re.search(r'(^|\s)[A-D][\)\.\:]', tl):
            has_choice = True
        if "please answer with the letter" in tl or "choose one of the following" in tl or "multiple choice" in tl:
            has_choice = True
        if has_choice:
            feats.append("has_choice")

        # Code patterns
        has_code = False
        code_markers = ["```", "def ", "class ", "import ", "#include", "public static", "System.out", "function ", "var ", "std::", "lambda "]
        for m in code_markers:
            if m.lower() in tl:
                has_code = True
                break
        if has_code:
            feats.append("has_code")

        # Language hints
        langs = ["python", "java", "c++", "cpp", "javascript", "typescript", "sql", "bash", "shell"]
        for lang in langs:
            if lang in tl:
                feats.append("lang=" + lang)

        # Math patterns
        has_math = False
        math_markers = ["integral", "derivative", "solve for", "equation", "algebra", "geometry", "probability", "statistic", "matrix"]
        for m in math_markers:
            if m in tl:
                has_math = True
                break
        if has_math:
            feats.append("has_math")

        # Punctuation features
        if "?" in txt:
            feats.append("has_qmark")
        if ":" in txt:
            feats.append("has_colon")

        # Combine
        return filt_tokens + feats

    def fit(self, texts, eval_names, labels):
        # First pass: build overall token counts
        overall_counts = Counter()
        label_indices = [self.label_to_idx[l] for l in labels]
        C = len(self.class_labels)

        N = len(texts)
        for i in range(N):
            tokens = self._tokenize(texts[i], eval_names[i])
            overall_counts.update(tokens)

        # Select vocabulary
        # Filter by min_token_count and select top max_vocab
        items = [(tok, cnt) for tok, cnt in overall_counts.items() if cnt >= self.min_token_count]
        items.sort(key=lambda x: x[1], reverse=True)
        if len(items) > self.max_vocab:
            items = items[: self.max_vocab]
        self.idx_to_token = [tok for tok, _ in items]
        self.vocab = {tok: i for i, tok in enumerate(self.idx_to_token)}
        V = len(self.vocab)
        if V == 0:
            # Degenerate case
            self.log_likelihood = np.zeros((C, 1), dtype=np.float64)
            # Prior based only on labels
            class_doc_counts = np.bincount(label_indices, minlength=C)
            self.log_prior = np.log((class_doc_counts + 1.0) / (N + float(C)))
            self.fitted = True
            return

        # Second pass: accumulate counts per class
        counts = np.zeros((C, V), dtype=np.uint32)
        class_token_totals = np.zeros(C, dtype=np.uint64)
        class_doc_counts = np.zeros(C, dtype=np.uint64)

        for i in range(N):
            cls = label_indices[i]
            class_doc_counts[cls] += 1
            tokens = self._tokenize(texts[i], eval_names[i])
            # Count tokens with cap
            cnt = Counter()
            for t in tokens:
                idx = self.vocab.get(t)
                if idx is not None:
                    if cnt.get(idx, 0) < self.per_doc_count_cap:
                        cnt[idx] = cnt.get(idx, 0) + 1
            if not cnt:
                continue
            for idx, c in cnt.items():
                counts[cls, idx] += c
                class_token_totals[cls] += c

        # Compute log likelihoods with Laplace smoothing
        alpha = self.alpha
        denom = (class_token_totals.astype(np.float64) + alpha * V).reshape(-1, 1)
        # To avoid division by zero when a class has zero tokens (unlikely)
        denom[denom == 0] = alpha * V
        log_likelihood = np.log((counts.astype(np.float64) + alpha) / denom)
        # Priors
        self.log_prior = np.log((class_doc_counts.astype(np.float64) + 1.0) / (N + float(C)))
        self.log_likelihood = log_likelihood
        self.fitted = True

    def predict_log_proba(self, text, eval_name):
        # Returns dict label -> log probability (unnormalized)
        if not self.fitted:
            # Uniform priors
            base = {l: -math.log(len(self.class_labels)) for l in self.class_labels}
            return base
        tokens = self._tokenize(text, eval_name)
        C = len(self.class_labels)
        V = len(self.vocab)
        log_scores = self.log_prior.copy()
        if V > 0:
            cnt = Counter()
            for t in tokens:
                idx = self.vocab.get(t)
                if idx is not None:
                    if cnt.get(idx, 0) < self.per_doc_count_cap:
                        cnt[idx] = cnt.get(idx, 0) + 1
            if cnt:
                # Add token contributions
                for idx, c in cnt.items():
                    log_scores += self.log_likelihood[:, idx] * c
        return {self.class_labels[i]: float(log_scores[i]) for i in range(C)}

    def predict(self, text, eval_name):
        logp = self.predict_log_proba(text, eval_name)
        # Return label with max log prob
        best = None
        best_val = -1e100
        for l, v in logp.items():
            if v > best_val:
                best_val = v
                best = l
        return best


class RouterModel:
    def __init__(self):
        self.nb = None
        self.eval_baseline = {}
        self.global_baseline = "cheap"
        self.trained = False

    def _compute_scores_and_labels(self, df):
        # Computes per-row score for each of the three tiers and best label
        # Returns filtered df with new columns and list of labels
        cheap_model = TIER_TO_MODEL["cheap"]
        mid_model = TIER_TO_MODEL["mid"]
        exp_model = TIER_TO_MODEL["expensive"]

        columns_needed = [
            cheap_model, mid_model, exp_model,
            cheap_model + "|total_cost",
            mid_model + "|total_cost",
            exp_model + "|total_cost",
            "prompt", "eval_name",
        ]
        for col in columns_needed:
            if col not in df.columns:
                return None, None

        # Coerce to numeric
        for col in [cheap_model, mid_model, exp_model,
                    cheap_model + "|total_cost",
                    mid_model + "|total_cost",
                    exp_model + "|total_cost"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Filter valid rows
        mask = (
            df[cheap_model].notna() &
            df[mid_model].notna() &
            df[exp_model].notna() &
            df[cheap_model + "|total_cost"].notna() &
            df[mid_model + "|total_cost"].notna() &
            df[exp_model + "|total_cost"].notna() &
            df["prompt"].notna() &
            df["eval_name"].notna()
        )
        dff = df.loc[mask].copy()
        if dff.empty:
            return None, None

        dff["score_cheap"] = dff[cheap_model] - LAMBDA * dff[cheap_model + "|total_cost"]
        dff["score_mid"] = dff[mid_model] - LAMBDA * dff[mid_model + "|total_cost"]
        dff["score_expensive"] = dff[exp_model] - LAMBDA * dff[exp_model + "|total_cost"]

        # Label best tier per row
        scores = dff[["score_cheap", "score_mid", "score_expensive"]].to_numpy()
        # Argmax across 3 columns
        best_idx = np.argmax(scores, axis=1)
        labels = [TIERS[i] for i in best_idx]
        return dff, labels

    def _train_nb(self, df, labels):
        # Prepare texts and eval_names
        texts = [_safe_text_from_prompt(x) for x in df["prompt"].tolist()]
        eval_names = [str(x) for x in df["eval_name"].tolist()]
        nb = NaiveBayesTextClassifier(class_labels=TIERS, alpha=1.0, max_vocab=30000, min_token_count=2, per_doc_count_cap=4)
        nb.fit(texts, eval_names, labels)
        self.nb = nb

    def _compute_eval_baseline(self, df):
        # For each eval_name, compute which tier has the highest average score
        if df.empty:
            self.eval_baseline = {}
            self.global_baseline = "cheap"
            return

        # Compute per-eval averages
        groups = df.groupby("eval_name")
        baseline = {}
        for ename, g in groups:
            c = float(g["score_cheap"].mean())
            m = float(g["score_mid"].mean())
            e = float(g["score_expensive"].mean())
            # Choose best based on highest average score
            if c >= m and c >= e:
                baseline[str(ename)] = "cheap"
            elif m >= c and m >= e:
                baseline[str(ename)] = "mid"
            else:
                baseline[str(ename)] = "expensive"
        self.eval_baseline = baseline

        # Global baseline across all
        c = float(df["score_cheap"].mean())
        m = float(df["score_mid"].mean())
        e = float(df["score_expensive"].mean())
        if c >= m and c >= e:
            self.global_baseline = "cheap"
        elif m >= c and m >= e:
            self.global_baseline = "mid"
        else:
            self.global_baseline = "expensive"

    def _fallback_heuristic(self, query, eval_name, candidate_models):
        # Very light heuristics if training unavailable
        ql = (query or "").lower()
        en = (eval_name or "").lower()
        has_code = any(k in ql for k in ["```", "def ", "class ", "import ", "#include", "public static", "function ", "var "])
        has_choice = bool(re.search(r'(^|\s)[A-D][\)\.\:]', ql)) or ("multiple choice" in ql)
        # Default
        choice = "cheap"
        if "mbpp" in en or "humaneval" in en or "leetcode" in en or has_code:
            choice = "mid"
        elif "mmlu" in en or has_choice:
            choice = "cheap"
        else:
            # Default to cheap to avoid cost
            choice = "cheap"

        # Map to available
        for preferred in [choice, "cheap", "mid", "expensive"]:
            if preferred in candidate_models:
                return preferred
        return candidate_models[0] if candidate_models else "cheap"

    def train(self):
        try:
            path = _find_data_path()
            if not path or not os.path.exists(path):
                self.trained = False
                return
            df = pd.read_csv(path)
            dff, labels = self._compute_scores_and_labels(df)
            if dff is None or labels is None or dff.empty:
                self.trained = False
                return
            self._train_nb(dff, labels)
            self._compute_eval_baseline(dff)
            self.trained = True
        except Exception:
            self.trained = False

    def _eval_baseline_choice(self, eval_name, candidate_models):
        en = str(eval_name) if eval_name is not None else ""
        best = self.eval_baseline.get(en, self.global_baseline)
        if best in candidate_models:
            return best
        # Fallback to cheapest available
        for t in TIERS:
            if t in candidate_models:
                return t
        return candidate_models[0] if candidate_models else "cheap"

    def route(self, query, eval_name, candidate_models):
        if not candidate_models:
            # Default return
            return "cheap"
        # Ensure candidate models contain some known tier
        available = set(candidate_models)
        # If not trained, fallback
        if not self.trained or self.nb is None or not self.nb.fitted:
            return self._fallback_heuristic(query, eval_name, candidate_models)

        text = _safe_text_from_prompt(query)
        # For very short inputs, rely more on eval baseline
        words = re.findall(r"[a-z0-9_]+", text.lower())
        char_len = len(text)
        has_code = any(k in text.lower() for k in ["```", "def ", "class ", "import ", "#include", "public static", "function ", "var "])
        has_choice = bool(re.search(r'(^|\s)[A-D][\)\.\:]', text.lower())) or ("multiple choice" in text.lower())

        use_baseline = False
        if len(words) < 10 or char_len < 50:
            use_baseline = True
        if not has_code and has_choice and len(words) < 60:
            # Multiple choice short questions likely cheap/mid
            use_baseline = True

        if use_baseline:
            baseline_choice = self._eval_baseline_choice(eval_name, candidate_models)
            if baseline_choice in available:
                return baseline_choice

        # Use NB prediction
        pred = self.nb.predict(text, eval_name)
        # Map to available
        if pred not in available:
            # Choose nearest preference order cheap -> mid -> expensive
            for t in TIERS:
                if t in available:
                    return t
            return candidate_models[0]
        return pred


# Global singleton and lock
_ROUTER_SINGLETON = None
_ROUTER_LOCK = threading.Lock()


def _get_router():
    global _ROUTER_SINGLETON
    if _ROUTER_SINGLETON is not None:
        return _ROUTER_SINGLETON
    with _ROUTER_LOCK:
        if _ROUTER_SINGLETON is None:
            router = RouterModel()
            router.train()
            _ROUTER_SINGLETON = router
    return _ROUTER_SINGLETON


class Solution:
    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        try:
            router = _get_router()
            choice = router.route(query, eval_name, candidate_models or TIERS)
            if candidate_models and choice not in set(candidate_models):
                # Fallback to cheapest available
                for t in TIERS:
                    if t in candidate_models:
                        return t
                return candidate_models[0]
            return choice if candidate_models else "cheap"
        except Exception:
            # Fallback conservative choice
            if candidate_models:
                for t in TIERS:
                    if t in candidate_models:
                        return t
                return candidate_models[0]
            return "cheap"