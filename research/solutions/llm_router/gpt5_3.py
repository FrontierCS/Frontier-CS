import os
import re
import warnings
import numpy as np
import pandas as pd

try:
    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.linear_model import SGDClassifier
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Module-level singleton
_ROUTER_SINGLETON = None


def _find_data_path():
    candidates = [
        "resources/reference_data.csv",
        os.path.join(os.getcwd(), "resources", "reference_data.csv"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "reference_data.csv"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _sanitize_text(s):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    try:
        s = str(s)
    except Exception:
        s = ""
    return s


def _safe_len(s):
    try:
        return len(s)
    except Exception:
        return 0


class _Router:
    def __init__(self):
        self.lambda_weight = 150.0
        self.tier_names = ["cheap", "mid", "expensive"]
        # Mapping tiers to concrete LLM columns expected in dataset
        self.tier_to_model = {
            "cheap": "mistralai/mistral-7b-chat",
            "mid": "mistralai/mixtral-8x7b-chat",
            "expensive": "gpt-4-1106-preview",
        }
        self.model_cost_cols = {m: f"{m}|total_cost" for m in self.tier_to_model.values()}
        self._fitted = False

        # ML components
        self.vectorizer = None
        self.model_correct_cls = {}  # tier -> classifier
        self.cost_params = {}  # tier -> (intercept, slope)
        self.eval_baseline = {}  # eval_name -> predicted tier
        self.global_default_tier = "cheap"
        self.have_data = False

        self._init()

    def _init(self):
        # Load dataset if available
        data_path = _find_data_path()
        if data_path is None:
            # No data; use pure heuristics
            self.have_data = False
            self._fitted = False
            return

        try:
            df = pd.read_csv(data_path, low_memory=False)
        except Exception:
            self.have_data = False
            self._fitted = False
            return

        # Check columns
        needed_cols = ["prompt", "eval_name"]
        cheap_model = self.tier_to_model["cheap"]
        mid_model = self.tier_to_model["mid"]
        exp_model = self.tier_to_model["expensive"]

        needed_cols.extend([cheap_model, mid_model, exp_model])
        needed_cols.extend([self.model_cost_cols[cheap_model], self.model_cost_cols[mid_model], self.model_cost_cols[exp_model]])

        cols_present = all(col in df.columns for col in needed_cols)
        if not cols_present:
            # Dataset doesn't have expected columns; fallback heuristics
            self.have_data = False
            self._fitted = False
            return

        self.have_data = True

        # Keep only required columns for memory efficiency
        df = df[needed_cols].copy()

        # Sanitize prompt and eval_name
        df["prompt"] = df["prompt"].map(_sanitize_text)
        df["eval_name"] = df["eval_name"].map(_sanitize_text)

        # Compute lengths
        df["_char_len"] = df["prompt"].map(_safe_len).astype(np.int32)

        # Prepare correctness arrays (0/1)
        y_correct = {}
        for tier, model in self.tier_to_model.items():
            y = pd.to_numeric(df[model], errors="coerce").fillna(0.0).values
            y_correct[tier] = (y >= 0.5).astype(np.int8)

        # Prepare cost arrays
        costs = {}
        for tier, model in self.tier_to_model.items():
            col = self.model_cost_cols[model]
            c = pd.to_numeric(df[col], errors="coerce").fillna(0.0).values.astype(np.float64)
            c[c < 0] = 0.0
            costs[tier] = c

        # Fit linear cost model: cost = a + b * char_len
        L = df["_char_len"].values.astype(np.float64)
        L_mean = float(np.mean(L)) if L.size > 0 else 0.0
        L_var = float(np.var(L)) if L.size > 0 else 0.0
        for tier in self.tier_names:
            c = costs[tier]
            # Only consider entries with positive cost
            mask = np.isfinite(c) & np.isfinite(L)
            if not np.any(mask):
                a, b = float(np.mean(c) if c.size > 0 else 0.0), 0.0
            else:
                Lm = L[mask]
                Cm = c[mask]
                if Lm.size < 2:
                    a = float(np.mean(Cm)) if Cm.size > 0 else 0.0
                    b = 0.0
                else:
                    L_mean_m = float(np.mean(Lm))
                    C_mean_m = float(np.mean(Cm))
                    denom = float(np.sum((Lm - L_mean_m) ** 2))
                    if denom <= 0:
                        b = 0.0
                    else:
                        b = float(np.sum((Lm - L_mean_m) * (Cm - C_mean_m)) / denom)
                    a = float(C_mean_m - b * L_mean_m)
                    if not np.isfinite(a):
                        a = float(np.mean(Cm))
                    if not np.isfinite(b):
                        b = 0.0
                    if b < 0:
                        # Costs should not decrease with length; clamp
                        b = 0.0
                    if a < 0:
                        a = 0.0
            self.cost_params[tier] = (a, b)

        # Compute oracle routing for each row based on utility: correctness - lambda * cost
        lambda_w = self.lambda_weight
        util_cols = {}
        for tier in self.tier_names:
            util_cols[tier] = y_correct[tier].astype(np.float64) - lambda_w * costs[tier]

        # Determine best tier per-row
        util_mat = np.vstack([util_cols["cheap"], util_cols["mid"], util_cols["expensive"]]).T
        best_idx = np.argmax(util_mat, axis=1)
        idx_to_tier = {0: "cheap", 1: "mid", 2: "expensive"}
        oracle_by_utility = np.vectorize(idx_to_tier.get)(best_idx)

        # Per-eval baseline: majority oracle choice
        eval_group = {}
        for e, t in zip(df["eval_name"].values.tolist(), oracle_by_utility.tolist()):
            if e not in eval_group:
                eval_group[e] = {}
            eval_group[e][t] = eval_group[e].get(t, 0) + 1
        for e, counts in eval_group.items():
            self.eval_baseline[e] = sorted(counts.items(), key=lambda kv: (-kv[1], self.tier_names.index(kv[0])))[0][0]

        # Global baseline
        global_counts = {}
        for t in oracle_by_utility:
            global_counts[t] = global_counts.get(t, 0) + 1
        if len(global_counts) > 0:
            self.global_default_tier = sorted(global_counts.items(), key=lambda kv: (-kv[1], self.tier_names.index(kv[0])))[0][0]
        else:
            self.global_default_tier = "cheap"

        # Train ML classifiers if sklearn available
        if SKLEARN_AVAILABLE:
            # Build texts
            texts = []
            evals = df["eval_name"].values.tolist()
            prompts = df["prompt"].values.tolist()
            for e, p in zip(evals, prompts):
                texts.append(f"[EVAL] {e} [PROMPT] {p}")

            # Vectorizer: Hashing for scalability
            self.vectorizer = HashingVectorizer(
                n_features=2 ** 18,
                analyzer="char_wb",
                ngram_range=(3, 5),
                alternate_sign=False,
                norm="l2",
                lowercase=True,
            )
            X = self.vectorizer.transform(texts)

            # Train per-tier classifiers for correctness
            self.model_correct_cls = {}
            for tier in self.tier_names:
                y = y_correct[tier].astype(np.int8)
                # Use SGDClassifier with log-loss to get predict_proba
                clf = SGDClassifier(
                    loss="log_loss",
                    penalty="l2",
                    alpha=1e-6,
                    random_state=42,
                    early_stopping=True,
                    validation_fraction=0.1,
                    n_iter_no_change=3,
                    max_iter=1000,
                    tol=1e-3,
                    fit_intercept=True,
                    learning_rate="optimal",
                )
                try:
                    clf.fit(X, y)
                except Exception:
                    # Fallback: if training fails, use heuristic by setting None
                    clf = None
                self.model_correct_cls[tier] = clf

            self._fitted = True
        else:
            self._fitted = False

        # Free memory
        del df

    def _estimate_cost(self, tier, query_len):
        a, b = self.cost_params.get(tier, (0.0, 0.0))
        est = a + b * float(query_len)
        if not np.isfinite(est) or est < 0:
            est = 0.0
        return est

    def _predict_probs(self, text):
        # Returns dict tier -> p_correct
        probs = {}
        if not SKLEARN_AVAILABLE or not self._fitted or self.vectorizer is None:
            # fallback uniform
            for t in self.tier_names:
                probs[t] = 0.5
            return probs

        try:
            X = self.vectorizer.transform([text])
        except Exception:
            for t in self.tier_names:
                probs[t] = 0.5
            return probs

        for t in self.tier_names:
            clf = self.model_correct_cls.get(t)
            if clf is None:
                probs[t] = 0.5
            else:
                try:
                    pr = clf.predict_proba(X)
                    if pr.shape[1] == 2:
                        probs[t] = float(pr[0, 1])
                    else:
                        # Unexpected shape; use middle or max
                        probs[t] = float(np.max(pr[0]))
                except Exception:
                    try:
                        # fallback using decision_function
                        dfun = clf.decision_function(X)
                        # logistic transform
                        probs[t] = 1.0 / (1.0 + float(np.exp(-float(dfun[0]))))
                    except Exception:
                        probs[t] = 0.5
        return probs

    def _choose_from_scores(self, scores, candidate_models):
        # scores: dict tier->score (higher is better)
        # Return best tier restricted to candidate_models
        # Keep original ordering fallback
        allowed = [m for m in self.tier_names if m in candidate_models]
        if not allowed:
            # No overlap; pick the first candidate to avoid invalid response
            return candidate_models[0] if candidate_models else "cheap"
        best_tier = max(allowed, key=lambda t: (scores.get(t, -1e9), -self.tier_names.index(t)))
        return best_tier

    def _pattern_heuristic(self, query, eval_name):
        # Simple rule-based fallback when no data/models available
        q = query.lower()
        e = (eval_name or "").lower()

        code_patterns = [
            r"\bpython\b", r"\bjava\b", r"\bc\+\+\b", r"\bc#\b", r"\bjavascript\b",
            r"\bfunction\b", r"\bclass\b", r"\bdef\b", r"```", r"\bcode\b", r"\bcompile\b",
        ]
        math_patterns = [
            r"\bprove\b", r"\btheorem\b", r"\blemma\b", r"\bequation\b",
            r"\bsolve\b", r"\bintegral\b", r"\bdifferential\b", r"\bsum\b",
            r"\bproduct\b", r"\bfactor\b", r"\bsimplify\b",
        ]
        mc_patterns = [
            r"\bwhich of the following\b", r"\bmultiple[- ]choice\b", r"\bchoose the\b",
            r"\bA\)\b", r"\bB\)\b", r"\bC\)\b", r"\bD\)\b",
            r"\(\s*A\s*\)", r"\(\s*B\s*\)", r"\(\s*C\s*\)", r"\(\s*D\s*\)",
            r"\boptions\b",
        ]

        def any_match(patterns):
            for p in patterns:
                if re.search(p, q):
                    return True
            return False

        if e in {"mbpp", "humaneval", "code", "apps", "ds1000"} or any_match(code_patterns):
            return "expensive"
        if e in {"gsm8k", "mathqa", "svamp", "amc", "aime", "math"} or any_match(math_patterns):
            return "expensive"
        if e.startswith("mmlu") or e in {"arc", "arc-challenge", "arc-easy", "hellaswag"} or any_match(mc_patterns):
            return "mid"
        # default
        return "cheap"

    def route(self, query, eval_name, candidate_models):
        # Compose text for model
        query = _sanitize_text(query)
        eval_name = _sanitize_text(eval_name)

        # Fast path heuristic if no data and no ML
        if not self.have_data and not self._fitted:
            tier_guess = self._pattern_heuristic(query, eval_name)
            # restrict to candidate_models
            if tier_guess in candidate_models:
                return tier_guess
            # Choose closest rank available
            for t in self.tier_names:
                if t in candidate_models:
                    return t
            # Fallback
            return candidate_models[0] if candidate_models else "cheap"

        # If we have eval_baseline and ML not trained
        if not self._fitted:
            # Use baseline per eval_name if available, else pattern heuristic
            tier_guess = self.eval_baseline.get(eval_name, self.global_default_tier if self.have_data else self._pattern_heuristic(query, eval_name))
            if tier_guess in candidate_models:
                return tier_guess
            for t in self.tier_names:
                if t in candidate_models:
                    return t
            return candidate_models[0] if candidate_models else "cheap"

        # ML-based expected utility routing
        text = f"[EVAL] {eval_name} [PROMPT] {query}"
        probs = self._predict_probs(text)

        L = _safe_len(query)
        scores = {}
        for t in self.tier_names:
            cost_est = self._estimate_cost(t, L)
            # Expected utility: P(correct) - lambda * cost_est
            scores[t] = float(probs.get(t, 0.5)) - self.lambda_weight * float(cost_est)

        # Choose best allowed
        chosen = self._choose_from_scores(scores, candidate_models)

        # Minor guard: if two scores are very close, prefer cheaper
        try:
            sorted_tiers = sorted(self.tier_names, key=lambda x: (-scores.get(x, -1e9), self.tier_names.index(x)))
            if len(sorted_tiers) >= 2:
                top, second = sorted_tiers[0], sorted_tiers[1]
                if abs(scores.get(top, 0) - scores.get(second, 0)) < 1e-6:
                    # Prefer cheaper among those allowed
                    for t in ["cheap", "mid", "expensive"]:
                        if t in candidate_models and t in [top, second]:
                            chosen = t
                            break
        except Exception:
            pass

        if chosen in candidate_models:
            return chosen
        # fallback to allowed by rank
        for t in self.tier_names:
            if t in candidate_models:
                return t
        return candidate_models[0] if candidate_models else "cheap"


class Solution:
    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        global _ROUTER_SINGLETON
        if _ROUTER_SINGLETON is None:
            _ROUTER_SINGLETON = _Router()
        # Ensure candidate_models validity
        if not candidate_models:
            candidate_models = ["cheap", "mid", "expensive"]
        # Sanitize candidate models: keep strings
        candidate_models = [str(m) for m in candidate_models]
        choice = _ROUTER_SINGLETON.route(query, eval_name, candidate_models)
        # Final guard
        if choice not in candidate_models:
            # Pick the first allowed in tier order
            for t in ["cheap", "mid", "expensive"]:
                if t in candidate_models:
                    return t
            return candidate_models[0]
        return choice