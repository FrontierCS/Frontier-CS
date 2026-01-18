import os
import re
import math
import pandas as pd
import numpy as np
from typing import Dict, List


class _HashingVectorizer:
    def __init__(self, n_features: int = 524288, max_tokens: int = 512, include_bigrams: bool = False):
        self.n_features = n_features
        self.max_tokens = max_tokens
        self.include_bigrams = include_bigrams
        self._token_re = re.compile(r"[A-Za-z0-9_]+")

    def _hash(self, key: str) -> int:
        return hash(key) % self.n_features

    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        # Lowercase for normalization
        text = text.lower()
        # Replace literal "\n" with newline to normalize formatting
        text = text.replace("\\n", "\n")
        tokens = self._token_re.findall(text)
        if len(tokens) > self.max_tokens:
            tokens = tokens[: self.max_tokens]
        return tokens

    def _add_flag_features(self, text: str, feats: Dict[int, float]):
        lower = text.lower()

        # Multiple-choice detection
        if ("please answer with the letter" in lower) or re.search(r"(^|[\n\s])([a-e])[\)\.]", lower):
            feats[self._hash("flag:mcq")] = feats.get(self._hash("flag:mcq"), 0.0) + 1.0

        # Code detection
        code_signals = ["```", "def ", "class ", "import ", "public static", "console.log", "function ", "#include", "using System"]
        if any(sig in lower for sig in code_signals):
            feats[self._hash("flag:code")] = feats.get(self._hash("flag:code"), 0.0) + 1.0

        # Math/quantitative detection
        math_signals = ["sqrt", "integral", "sum_{", "\\frac", "equation", "polynomial", "derivative", "proof", "theorem"]
        if any(sig in lower for sig in math_signals):
            feats[self._hash("flag:math")] = feats.get(self._hash("flag:math"), 0.0) + 1.0

        # Reasoning/cot hint
        cot_signals = ["let's think", "step by step", "explain your reasoning", "reason step by step"]
        if any(sig in lower for sig in cot_signals):
            feats[self._hash("flag:cot")] = feats.get(self._hash("flag:cot"), 0.0) + 1.0

        # JSON/SQL detection
        if "select " in lower or "create table" in lower or "insert into" in lower:
            feats[self._hash("flag:sql")] = feats.get(self._hash("flag:sql"), 0.0) + 1.0
        if "{" in lower and "}" in lower and ":" in lower:
            feats[self._hash("flag:json")] = feats.get(self._hash("flag:json"), 0.0) + 1.0

    def transform(self, text: str, eval_name: str = "") -> Dict[int, float]:
        feats: Dict[int, float] = {}
        if text is None:
            text = ""
        tokens = self._tokenize(text)

        # Unigram features
        for t in tokens:
            idx = self._hash("w:" + t)
            feats[idx] = feats.get(idx, 0.0) + 1.0

        # Bigram features (optional)
        if self.include_bigrams and len(tokens) > 1:
            for a, b in zip(tokens, tokens[1:]):
                idx = self._hash("b:" + a + "_" + b)
                feats[idx] = feats.get(idx, 0.0) + 1.0

        # Eval name categorical feature
        if eval_name:
            idx = self._hash("eval:" + str(eval_name))
            feats[idx] = feats.get(idx, 0.0) + 2.0  # slightly higher weight to task identity

        # Length-based features
        text_raw = text if isinstance(text, str) else str(text)
        num_chars = len(text_raw)
        num_tokens = len(tokens)
        num_lines = text_raw.count("\n") + 1

        len_bin = int(math.log2(num_tokens + 1)) if num_tokens > 0 else 0
        chars_bin = int(math.log2(num_chars + 1)) if num_chars > 0 else 0
        lines_bin = int(math.log2(num_lines + 1)) if num_lines > 0 else 0

        feats[self._hash(f"len_bin:{len_bin}")] = feats.get(self._hash(f"len_bin:{len_bin}"), 0.0) + 1.0
        feats[self._hash(f"chars_bin:{chars_bin}")] = feats.get(self._hash(f"chars_bin:{chars_bin}"), 0.0) + 1.0
        feats[self._hash(f"lines_bin:{lines_bin}")] = feats.get(self._hash(f"lines_bin:{lines_bin}"), 0.0) + 1.0

        # Heuristic flags
        self._add_flag_features(text_raw, feats)

        return feats


class _NaiveBayesRouter:
    def __init__(self, n_features: int = 524288, alpha: float = 0.5, prior_alpha: float = 1.0):
        self.n_features = n_features
        self.alpha = alpha
        self.prior_alpha = prior_alpha
        self.C = 3  # cheap/mid/expensive
        self.trained = False

        # Model parameters
        self.log_probs = None  # shape (C, n_features), float32
        self.log_priors = None  # shape (C,), float32

        # For fallback heuristics based on eval_name
        self.eval_name_priors = {}

    def fit(self, df: pd.DataFrame, tier_models: Dict[str, str], lambda_cost: float = 150.0):
        # Determine labels from reference data using the three tier models
        cheap_model = tier_models["cheap"]
        mid_model = tier_models["mid"]
        expensive_model = tier_models["expensive"]

        def col_exists(col: str) -> bool:
            return col in df.columns

        # Validate columns exist; otherwise early return with untrained status
        required_cols = [
            cheap_model, mid_model, expensive_model,
            f"{cheap_model}|total_cost", f"{mid_model}|total_cost", f"{expensive_model}|total_cost"
        ]
        if not all(col_exists(c) for c in required_cols):
            # Cannot train without proper columns
            self.trained = False
            return

        # Extract arrays (fill NaNs)
        corr_cheap = df[cheap_model].astype(float).fillna(0.0).values
        corr_mid = df[mid_model].astype(float).fillna(0.0).values
        corr_exp = df[expensive_model].astype(float).fillna(0.0).values

        cost_cheap = df[f"{cheap_model}|total_cost"].astype(float).replace([np.inf, -np.inf], np.nan).fillna(1e9).values
        cost_mid = df[f"{mid_model}|total_cost"].astype(float).replace([np.inf, -np.inf], np.nan).fillna(1e9).values
        cost_exp = df[f"{expensive_model}|total_cost"].astype(float).replace([np.inf, -np.inf], np.nan).fillna(1e9).values

        # Compute per-tier scores (correctness - lambda*cost)
        s_cheap = corr_cheap - lambda_cost * cost_cheap
        s_mid = corr_mid - lambda_cost * cost_mid
        s_exp = corr_exp - lambda_cost * cost_exp

        scores = np.vstack([s_cheap, s_mid, s_exp]).T  # shape (N, 3)
        y = np.argmax(scores, axis=1).astype(np.int64)  # labels 0,1,2

        # Build featurizer
        vectorizer = _HashingVectorizer(n_features=self.n_features, max_tokens=512, include_bigrams=False)

        # Initialize counts
        counts = np.zeros((self.C, self.n_features), dtype=np.float32)
        doc_counts = np.zeros(self.C, dtype=np.int64)
        total_token_counts = np.zeros(self.C, dtype=np.float64)

        # Train (single pass)
        prompts = df["prompt"].astype(str).values
        eval_names = df["eval_name"].astype(str).fillna("").values

        # Build simple per-eval_name priors (for fallback/adjustment)
        eval_name_counts = {}
        for ename, label in zip(eval_names, y):
            if ename not in eval_name_counts:
                eval_name_counts[ename] = np.zeros(self.C, dtype=np.float64)
            eval_name_counts[ename][label] += 1.0

        # Accumulate token counts
        for text, label, ename in zip(prompts, y, eval_names):
            feats = vectorizer.transform(text, ename)
            if not feats:
                doc_counts[label] += 1
                continue
            # Accumulate counts for class
            s = 0.0
            for idx, val in feats.items():
                counts[label, idx] += float(val)
                s += float(val)
            total_token_counts[label] += s
            doc_counts[label] += 1

        # Compute log probabilities with additive smoothing
        C = self.C
        n_features = self.n_features
        alpha = float(self.alpha)
        log_probs = np.zeros_like(counts, dtype=np.float32)
        for c in range(C):
            denom_c = total_token_counts[c] + alpha * n_features
            # Avoid log(0)
            log_counts_c = np.log(counts[c] + alpha, dtype=np.float64)
            log_probs_c = log_counts_c - math.log(denom_c)
            log_probs[c] = log_probs_c.astype(np.float32)

        # Compute log priors
        total_docs = float(np.sum(doc_counts))
        priors = (doc_counts.astype(np.float64) + self.prior_alpha) / (total_docs + self.prior_alpha * C)
        log_priors = np.log(priors).astype(np.float32)

        self.log_probs = log_probs
        self.log_priors = log_priors
        self.trained = True

        # Prepare eval_name priors (smoothed)
        eval_priors = {}
        for ename, arr in eval_name_counts.items():
            total = float(np.sum(arr))
            if total <= 0:
                eval_priors[ename] = np.log(np.ones(C) / C).astype(np.float32)
            else:
                smoothed = (arr + self.prior_alpha) / (total + self.prior_alpha * C)
                eval_priors[ename] = np.log(smoothed).astype(np.float32)
        self.eval_name_priors = eval_priors

    def predict_label(self, text: str, eval_name: str = "") -> int:
        if not self.trained or self.log_probs is None or self.log_priors is None:
            # Default to cheap
            return 0
        vectorizer = _HashingVectorizer(n_features=self.n_features, max_tokens=512, include_bigrams=False)
        feats = vectorizer.transform(text, eval_name)
        scores = self.log_priors.copy()
        # Add optional eval_name prior adjustment if known
        if eval_name in self.eval_name_priors:
            scores = scores + 0.5 * self.eval_name_priors[eval_name]  # small weight

        if feats:
            for idx, val in feats.items():
                # Add contribution from token counts for each class
                token_logprob = self.log_probs[:, idx]
                scores += float(val) * token_logprob

        # Argmax over classes
        return int(np.argmax(scores))


class Solution:
    def __init__(self):
        self._initialized = False
        self._router = None
        self._tier_order = ["cheap", "mid", "expensive"]
        self._tier_to_index = {name: i for i, name in enumerate(self._tier_order)}
        self._lambda_cost = 150.0

    def _init(self):
        if self._initialized:
            return

        # Default mapping of tiers to reference models
        tier_models = {
            "cheap": "mistralai/mistral-7b-chat",
            "mid": "mistralai/mixtral-8x7b-chat",
            "expensive": "gpt-4-1106-preview",
        }

        # Load reference data
        df = None
        possible_paths = [
            os.path.join("resources", "reference_data.csv"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "reference_data.csv"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                try:
                    df = pd.read_csv(p)
                    break
                except Exception:
                    df = None

        self._router = _NaiveBayesRouter(n_features=524288, alpha=0.5, prior_alpha=1.0)

        if df is not None and "prompt" in df.columns and "eval_name" in df.columns:
            try:
                self._router.fit(df, tier_models, lambda_cost=self._lambda_cost)
            except Exception:
                # If training fails, mark as untrained
                self._router.trained = False
        else:
            self._router.trained = False

        self._initialized = True

    def _nearest_available_tier(self, predicted_index: int, candidate_models: List[str]) -> str:
        # If predicted tier is available, return it directly
        pred_name = self._tier_order[predicted_index]
        if pred_name in candidate_models:
            return pred_name

        # Otherwise, pick the closest by index distance among available tiers
        available_indices = [self._tier_to_index[m] for m in candidate_models if m in self._tier_to_index]
        if not available_indices:
            # Fallback to first candidate if they are not the expected tier names
            return candidate_models[0]
        nearest_idx = min(available_indices, key=lambda i: abs(i - predicted_index))
        for name, idx in self._tier_to_index.items():
            if idx == nearest_idx:
                return name
        return candidate_models[0]

    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        if not self._initialized:
            self._init()

        # Basic validation
        if not candidate_models:
            return "cheap"
        # If invalid list (not the expected tier strings), return first element
        if not all(isinstance(m, str) for m in candidate_models):
            return candidate_models[0]

        # Predict with router (if trained), otherwise use simple heuristics
        if self._router is not None and self._router.trained:
            pred_idx = self._router.predict_label(query or "", eval_name or "")
            return self._nearest_available_tier(pred_idx, candidate_models)

        # Heuristic fallback if training failed or data unavailable
        name = (eval_name or "").lower()
        text = (query or "").lower()

        difficult_signals = [
            "let's think", "step by step", "prove", "integral", "derivative", "optimize", "algorithm",
            "write a function", "implement", "code", "python", "c++", "java", "bug", "fix", "mbpp", "humaneval", "gsm8k", "math"
        ]
        if any(sig in text for sig in difficult_signals) or any(sig in name for sig in ["mbpp", "humaneval", "gsm8k", "math"]):
            # Prefer mid or expensive if available
            if "mid" in candidate_models:
                return "mid"
            if "expensive" in candidate_models:
                return "expensive"
            return "cheap"

        # Multiple-choice tasks often easy
        if re.search(r"(^|[\n\s])([a-e])[\)\.]", text) or "please answer with the letter" in text or "mmlu" in name or "hellaswag" in name:
            if "cheap" in candidate_models:
                return "cheap"
            if "mid" in candidate_models:
                return "mid"
            return "expensive"

        # Default to cheap for general queries
        if "cheap" in candidate_models:
            return "cheap"
        # If cheap not available, prefer mid over expensive
        if "mid" in candidate_models:
            return "mid"
        return candidate_models[0]