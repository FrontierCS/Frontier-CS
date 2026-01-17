import os
import re
import math
import numpy as np

try:
    import pandas as pd
except Exception:
    pd = None


class _BinaryMultinomialNB:
    __slots__ = (
        "n_features",
        "alpha",
        "feature_count",
        "class_count",
        "total_tokens",
        "log_prior",
        "log_condprob",
        "finalized",
    )

    def __init__(self, n_features: int, alpha: float = 0.5):
        self.n_features = int(n_features)
        self.alpha = float(alpha)
        self.feature_count = np.zeros((2, self.n_features), dtype=np.float32)
        self.class_count = np.zeros(2, dtype=np.int64)
        self.total_tokens = np.zeros(2, dtype=np.float64)
        self.log_prior = np.zeros(2, dtype=np.float32)
        self.log_condprob = None
        self.finalized = False

    def update(self, idx: np.ndarray, cnt: np.ndarray, y: int):
        y = 1 if y else 0
        self.class_count[y] += 1
        s = float(cnt.sum()) if cnt.size else 0.0
        self.total_tokens[y] += s
        if idx.size:
            self.feature_count[y, idx] += cnt

    def finalize(self):
        if self.finalized:
            return
        alpha = self.alpha
        nfeat = self.n_features

        total = self.class_count.sum()
        self.log_prior = np.log((self.class_count + 1.0) / (total + 2.0)).astype(np.float32)

        self.log_condprob = np.empty_like(self.feature_count, dtype=np.float32)
        for y in (0, 1):
            denom = self.total_tokens[y] + alpha * nfeat
            self.log_condprob[y] = np.log((self.feature_count[y] + alpha) / denom, dtype=np.float32)

        self.feature_count = None
        self.finalized = True

    def logit_p_correct(self, idx: np.ndarray, cnt: np.ndarray) -> float:
        if not self.finalized:
            self.finalize()
        if idx.size:
            ll0 = float(self.log_prior[0] + (cnt * self.log_condprob[0, idx]).sum())
            ll1 = float(self.log_prior[1] + (cnt * self.log_condprob[1, idx]).sum())
        else:
            ll0 = float(self.log_prior[0])
            ll1 = float(self.log_prior[1])
        return ll1 - ll0


class Solution:
    _initialized = False
    _init_failed = False

    _N_FEATURES = 1 << 18
    _ALPHA = 0.5
    _LAMBDA = 150.0
    _LOGIT_TEMP = 0.85

    _DEFAULT_ANCHORS = {
        "cheap": "mistralai/mistral-7b-chat",
        "mid": "mistralai/mixtral-8x7b-chat",
        "expensive": "gpt-4-1106-preview",
    }

    _DEFAULT_COSTS = {"cheap": 1.8e-5, "mid": 6.8e-5, "expensive": 8.8e-4}

    _TOKEN_RE = re.compile(r"[a-zA-Z_]+|\d+|[^\s]", re.UNICODE)
    _WS_RE = re.compile(r"\s+")
    _MATH_RE = re.compile(r"(\bprove\b|\bderive\b|\btheorem\b|\bintegral\b|\bderivative\b|\bequation\b|\\frac|\\int|\\sum|[∑∫√≈≠≤≥])", re.IGNORECASE)
    _CODE_RE = re.compile(r"(```|^\s*def\s+|^\s*class\s+|\bimport\s+\w+|\breturn\b|\bfor\s*\(|\bwhile\s*\(|\bpublic\s+static\b|\bconsole\.log\b|\bSELECT\b|\bFROM\b|\bJOIN\b)", re.IGNORECASE | re.MULTILINE)
    _CHOICE_RE = re.compile(r"(\n\s*[A-D]\)|\bA\)|\bB\)|\bC\)|\bD\)|\bE\))", re.IGNORECASE)

    _anchors = None
    _tier_cost = None
    _nbs = None
    _available_tiers = ("cheap", "mid", "expensive")

    def __init__(self):
        pass

    @classmethod
    def _data_path(cls) -> str:
        p1 = os.path.join("resources", "reference_data.csv")
        if os.path.exists(p1):
            return p1
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            problem_dir = os.path.dirname(os.path.dirname(base))
            p2 = os.path.join(problem_dir, "resources", "reference_data.csv")
            if os.path.exists(p2):
                return p2
        except Exception:
            pass
        return p1

    @classmethod
    def _safe_hash_idx(cls, token: str) -> int:
        return (hash(token) & 0x7FFFFFFF) % cls._N_FEATURES

    @classmethod
    def _extract_tokens(cls, query: str, eval_name: str) -> list:
        if query is None:
            query = ""
        if eval_name is None:
            eval_name = ""
        q = query.replace("\\n", " ").replace("\n", " ")
        q = cls._WS_RE.sub(" ", q).strip()
        ev = eval_name.strip().lower()
        s = (ev + " " + q).lower()

        toks = cls._TOKEN_RE.findall(s)
        if len(toks) > 260:
            toks = toks[:200] + toks[-60:]

        features = []
        if ev:
            features.append("__EVAL__=" + ev)

        n = len(query)
        if n < 80:
            features.append("__LEN__=0")
        elif n < 200:
            features.append("__LEN__=1")
        elif n < 450:
            features.append("__LEN__=2")
        elif n < 900:
            features.append("__LEN__=3")
        else:
            features.append("__LEN__=4")

        nd = sum(ch.isdigit() for ch in query)
        if nd == 0:
            features.append("__DIGITS__=0")
        elif nd < 5:
            features.append("__DIGITS__=1")
        elif nd < 20:
            features.append("__DIGITS__=2")
        else:
            features.append("__DIGITS__=3")

        if cls._CODE_RE.search(query):
            features.append("__HAS_CODE__")
        if cls._MATH_RE.search(query):
            features.append("__HAS_MATH__")
        if cls._CHOICE_RE.search(query):
            features.append("__HAS_CHOICES__")

        out = toks + features

        # Light bigrams for early tokens
        m = min(len(toks), 80)
        for i in range(m - 1):
            a = toks[i]
            b = toks[i + 1]
            if a.isalpha() and b.isalpha():
                out.append(a + "_" + b)

        return out

    @classmethod
    def _tokens_to_sparse(cls, tokens: list) -> tuple:
        d = {}
        for t in tokens:
            idx = cls._safe_hash_idx(t)
            d[idx] = d.get(idx, 0.0) + 1.0
        if not d:
            return np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32)
        idx = np.fromiter(d.keys(), dtype=np.int32, count=len(d))
        cnt = np.fromiter(d.values(), dtype=np.float32, count=len(d))
        return idx, cnt

    @classmethod
    def _infer_anchors_and_costs(cls, path: str):
        if pd is None:
            cls._anchors = dict(cls._DEFAULT_ANCHORS)
            cls._tier_cost = dict(cls._DEFAULT_COSTS)
            return

        try:
            header = pd.read_csv(path, nrows=0)
            cols = list(header.columns)
        except Exception:
            cls._anchors = dict(cls._DEFAULT_ANCHORS)
            cls._tier_cost = dict(cls._DEFAULT_COSTS)
            return

        def_present = all(m in cols and (m + "|total_cost") in cols for m in cls._DEFAULT_ANCHORS.values())
        if def_present:
            cls._anchors = dict(cls._DEFAULT_ANCHORS)
            tier_cost = {}
            try:
                usecols = [m + "|total_cost" for m in cls._DEFAULT_ANCHORS.values()]
                sums = {c: 0.0 for c in usecols}
                cnts = {c: 0 for c in usecols}
                for chunk in pd.read_csv(path, usecols=usecols, chunksize=5000):
                    for c in usecols:
                        arr = pd.to_numeric(chunk[c], errors="coerce").to_numpy(dtype=np.float64, copy=False)
                        mask = np.isfinite(arr)
                        if mask.any():
                            sums[c] += float(arr[mask].sum())
                            cnts[c] += int(mask.sum())
                for tier, m in cls._DEFAULT_ANCHORS.items():
                    c = m + "|total_cost"
                    if cnts[c] > 0:
                        tier_cost[tier] = max(1e-12, sums[c] / cnts[c])
                    else:
                        tier_cost[tier] = cls._DEFAULT_COSTS.get(tier, 1e-4)
            except Exception:
                tier_cost = dict(cls._DEFAULT_COSTS)
            cls._tier_cost = tier_cost
            return

        cost_cols = [c for c in cols if c.endswith("|total_cost")]
        base_models = [c[:-11] for c in cost_cols]  # remove "|total_cost"
        pairs = [(base, base + "|total_cost") for base in base_models if (base in cols)]
        if len(pairs) < 3:
            cls._anchors = dict(cls._DEFAULT_ANCHORS)
            cls._tier_cost = dict(cls._DEFAULT_COSTS)
            return

        sums = {base: 0.0 for base, _ in pairs}
        cnts = {base: 0 for base, _ in pairs}
        try:
            usecols = [c for _, c in pairs]
            for chunk in pd.read_csv(path, usecols=usecols, chunksize=5000):
                for base, c in pairs:
                    arr = pd.to_numeric(chunk[c], errors="coerce").to_numpy(dtype=np.float64, copy=False)
                    mask = np.isfinite(arr)
                    if mask.any():
                        sums[base] += float(arr[mask].sum())
                        cnts[base] += int(mask.sum())
        except Exception:
            cls._anchors = dict(cls._DEFAULT_ANCHORS)
            cls._tier_cost = dict(cls._DEFAULT_COSTS)
            return

        avg = []
        for base, _ in pairs:
            if cnts[base] > 0:
                avg.append((sums[base] / cnts[base], base))
        avg.sort(key=lambda x: x[0])
        if len(avg) < 3:
            cls._anchors = dict(cls._DEFAULT_ANCHORS)
            cls._tier_cost = dict(cls._DEFAULT_COSTS)
            return

        cheap = avg[0][1]
        expensive = avg[-1][1]
        mid = avg[len(avg) // 2][1]
        cls._anchors = {"cheap": cheap, "mid": mid, "expensive": expensive}
        cls._tier_cost = {
            "cheap": float(avg[0][0]),
            "mid": float(avg[len(avg) // 2][0]),
            "expensive": float(avg[-1][0]),
        }

    @classmethod
    def _train(cls):
        path = cls._data_path()
        cls._infer_anchors_and_costs(path)

        cls._nbs = {tier: _BinaryMultinomialNB(cls._N_FEATURES, cls._ALPHA) for tier in cls._available_tiers}

        if pd is None:
            cls._initialized = True
            return

        anchors = cls._anchors
        usecols = ["prompt", "eval_name"]
        for tier in cls._available_tiers:
            m = anchors.get(tier)
            if m:
                usecols.append(m)
        # We'll not need costs during training, only correctness.
        # Still, ensure columns exist in file; otherwise training will likely fail safely.

        try:
            for chunk in pd.read_csv(path, usecols=usecols, chunksize=2000):
                prompts = chunk["prompt"].astype(str).tolist()
                evals = chunk["eval_name"].astype(str).tolist()

                ys = {}
                for tier in cls._available_tiers:
                    m = anchors.get(tier)
                    if m and m in chunk.columns:
                        arr = pd.to_numeric(chunk[m], errors="coerce").to_numpy(dtype=np.float32, copy=False)
                        ys[tier] = arr
                    else:
                        ys[tier] = None

                for i in range(len(prompts)):
                    q = prompts[i]
                    ev = evals[i]
                    tokens = cls._extract_tokens(q, ev)
                    idx, cnt = cls._tokens_to_sparse(tokens)
                    for tier in cls._available_tiers:
                        arr = ys.get(tier)
                        if arr is None:
                            continue
                        v = arr[i]
                        if not np.isfinite(v):
                            continue
                        cls._nbs[tier].update(idx, cnt, 1 if v >= 0.5 else 0)
        except Exception:
            cls._init_failed = True
            cls._initialized = True
            return

        for tier in cls._available_tiers:
            cls._nbs[tier].finalize()

        cls._initialized = True

    @classmethod
    def _ensure_init(cls):
        if cls._initialized:
            return
        try:
            cls._train()
        except Exception:
            cls._init_failed = True
            cls._initialized = True

    @classmethod
    def _fallback(cls, query: str, eval_name: str, candidate_models: list) -> str:
        if not candidate_models:
            return "cheap"
        q = (query or "").lower()
        ev = (eval_name or "").lower()

        if "mbpp" in ev or "humaneval" in ev or "code" in ev:
            if "expensive" in candidate_models and (len(q) > 500 or "recursion" in q or "dynamic programming" in q):
                return "expensive"
            if "mid" in candidate_models:
                return "mid"
            return candidate_models[0]

        if "mmlu" in ev or "hellaswag" in ev or "arc" in ev:
            if "cheap" in candidate_models:
                return "cheap"
            return candidate_models[0]

        if "math" in ev or "gsm" in ev or "proof" in q or "derive" in q:
            if "expensive" in candidate_models:
                return "expensive"
            if "mid" in candidate_models:
                return "mid"
            return candidate_models[0]

        if "expensive" in candidate_models and (len(q) > 900):
            return "expensive"
        if "mid" in candidate_models and (len(q) > 350):
            return "mid"
        if "cheap" in candidate_models:
            return "cheap"
        return candidate_models[0]

    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        self.__class__._ensure_init()

        if not candidate_models:
            return "cheap"

        cm_set = set(candidate_models)
        if self.__class__._init_failed or self.__class__._nbs is None:
            out = self.__class__._fallback(query, eval_name, candidate_models)
            return out if out in cm_set else candidate_models[0]

        tokens = self.__class__._extract_tokens(query or "", eval_name or "")
        idx, cnt = self.__class__._tokens_to_sparse(tokens)

        tier_cost = self.__class__._tier_cost or self.__class__._DEFAULT_COSTS
        lam = self.__class__._LAMBDA
        temp = self.__class__._LOGIT_TEMP

        best_tier = None
        best_utility = -1e18

        for tier in self.__class__._available_tiers:
            if tier not in cm_set:
                continue
            nb = self.__class__._nbs.get(tier)
            if nb is None:
                continue
            logit = nb.logit_p_correct(idx, cnt)
            logit *= temp
            if logit >= 0:
                p = 1.0 / (1.0 + math.exp(-logit))
            else:
                e = math.exp(logit)
                p = e / (1.0 + e)
            cost = float(tier_cost.get(tier, self.__class__._DEFAULT_COSTS.get(tier, 1e-4)))
            utility = p - lam * cost
            if utility > best_utility:
                best_utility = utility
                best_tier = tier

        if best_tier is None:
            out = self.__class__._fallback(query, eval_name, candidate_models)
            return out if out in cm_set else candidate_models[0]
        return best_tier