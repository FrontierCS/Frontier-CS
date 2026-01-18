import os
import re
import csv
import math
import binascii
from collections import Counter
from typing import List, Dict, Optional, Tuple

import numpy as np


_WORD_RE = re.compile(r"[a-z0-9_]+")
_MC_RE = re.compile(r"(^|\n|\s)([a-d]|[a-e]|[a-f]|[a-g]|[a-h])[\)\.\:]\s", re.IGNORECASE)
_HAS_LETTER_CHOICES_RE = re.compile(r"(^|\n).*?\bA[\)\.\:]\s.*?\bB[\)\.\:]\s.*?\bC[\)\.\:]\s", re.IGNORECASE | re.DOTALL)
_CODE_HINT_RE = re.compile(r"(^|\n)\s*(def|class)\s+[A-Za-z_]\w*\s*\(", re.MULTILINE)
_STACKTRACE_RE = re.compile(r"Traceback \(most recent call last\):")
_JSONISH_RE = re.compile(r"[\{\}\[\]:,]\s*\"")
_MATH_RE = re.compile(r"(\bprove\b|\bderive\b|\bintegral\b|\bdifferentiate\b|\bgradient\b|\btheorem\b|\blemma\b|∫|∑|π|√|≈|≤|≥|≠)")


def _crc32_idx(token: str, mask: int) -> int:
    return binascii.crc32(token.encode("utf-8")) & mask


def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _safe_float(x: str, default: float = 0.0) -> float:
    if x is None:
        return default
    x = x.strip()
    if not x:
        return default
    try:
        return float(x)
    except Exception:
        return default


def _normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\\n", "\n")
    return s


def _extract_tokens(query: str, eval_name: str, max_words: int = 160) -> List[str]:
    q = _normalize_text(query).lower()
    tokens = _WORD_RE.findall(q)
    if len(tokens) > max_words:
        tokens = tokens[:max_words]

    feats = []
    if eval_name:
        feats.append(f"__eval__{eval_name.lower()}")

    qlen = len(q)
    if qlen < 80:
        feats.append("__len__xs")
    elif qlen < 200:
        feats.append("__len__s")
    elif qlen < 500:
        feats.append("__len__m")
    elif qlen < 1200:
        feats.append("__len__l")
    else:
        feats.append("__len__xl")

    digit_ratio = (sum(c.isdigit() for c in q) / max(1, qlen))
    if digit_ratio > 0.12:
        feats.append("__digits__hi")
    elif digit_ratio > 0.05:
        feats.append("__digits__med")
    else:
        feats.append("__digits__lo")

    if "```" in q:
        feats.append("__codeblock__")
    if _CODE_HINT_RE.search(q) or "import " in q or " from " in q or "def " in q:
        feats.append("__code__")
    if _STACKTRACE_RE.search(q) or "exception" in q or "error:" in q or "segmentation fault" in q:
        feats.append("__debug__")
    if _JSONISH_RE.search(q) or ("{" in q and "}" in q and ":" in q):
        feats.append("__json__")
    if _MATH_RE.search(q):
        feats.append("__math__")
    if _MC_RE.search(q) or _HAS_LETTER_CHOICES_RE.search(q):
        feats.append("__multichoice__")
    if "step by step" in q or "chain of thought" in q:
        feats.append("__cot_req__")
    if "write a function" in q or "implement" in q or "time complexity" in q or "big-o" in q:
        feats.append("__algo__")
    if "explain" in q or "why" in q or "compare" in q:
        feats.append("__explain__")

    # Add word bigrams (limited)
    bigrams = []
    lim = min(len(tokens), 60)
    for i in range(lim - 1):
        bigrams.append(tokens[i] + "_" + tokens[i + 1])

    return tokens + bigrams + feats


class _BinaryNBRouter:
    def __init__(self, dim_pow2: int = 18, alpha: float = 0.5):
        self.dim = 1 << dim_pow2
        self.mask = self.dim - 1
        self.alpha = float(alpha)

        self.tiers = ("cheap", "mid", "expensive")
        self.pos_counts = {t: np.zeros(self.dim, dtype=np.int32) for t in self.tiers}
        self.neg_counts = {t: np.zeros(self.dim, dtype=np.int32) for t in self.tiers}
        self.pos_total = {t: 0 for t in self.tiers}
        self.neg_total = {t: 0 for t in self.tiers}
        self.pos_prior = {t: 0.5 for t in self.tiers}

        self.loglik_pos = {}
        self.loglik_neg = {}

        self.cost_est = {t: 1e-4 for t in self.tiers}
        self.trained = False

    def _hash_counts(self, tokens: List[str]) -> Counter:
        c = Counter()
        m = self.mask
        for tok in tokens:
            c[_crc32_idx(tok, m)] += 1
        return c

    def train(
        self,
        rows: List[Dict[str, str]],
        model_cols: Dict[str, str],
        cost_cols: Dict[str, str],
        cost_est: Dict[str, float],
    ) -> None:
        self.cost_est.update(cost_est)

        for row in rows:
            prompt = row.get("prompt", "") or ""
            eval_name = row.get("eval_name", "") or ""
            tokens = _extract_tokens(prompt, eval_name)
            if not tokens:
                continue
            hcnt = self._hash_counts(tokens)

            for tier in self.tiers:
                mcol = model_cols.get(tier)
                if not mcol:
                    continue
                y = _safe_float(row.get(mcol, ""), default=float("nan"))
                if not (y == y):
                    continue
                correct = (y >= 0.5)

                if correct:
                    pc = self.pos_counts[tier]
                    for idx, cnt in hcnt.items():
                        pc[idx] += cnt
                    self.pos_total[tier] += sum(hcnt.values())
                else:
                    nc = self.neg_counts[tier]
                    for idx, cnt in hcnt.items():
                        nc[idx] += cnt
                    self.neg_total[tier] += sum(hcnt.values())

        for tier in self.tiers:
            pt = self.pos_total[tier]
            nt = self.neg_total[tier]
            denom = pt + nt
            if denom <= 0:
                self.pos_prior[tier] = 0.5
            else:
                # Slightly smoothed
                self.pos_prior[tier] = (pt + 1.0) / (denom + 2.0)

            alpha = self.alpha
            dim = self.dim

            pos = self.pos_counts[tier].astype(np.float32)
            neg = self.neg_counts[tier].astype(np.float32)

            pos_denom = float(pt) + alpha * dim
            neg_denom = float(nt) + alpha * dim

            self.loglik_pos[tier] = np.log((pos + alpha) / pos_denom, dtype=np.float32)
            self.loglik_neg[tier] = np.log((neg + alpha) / neg_denom, dtype=np.float32)

        self.trained = True

    def predict_p_correct(self, tokens: List[str], tier: str) -> float:
        if not self.trained or tier not in self.tiers:
            return 0.5
        hcnt = self._hash_counts(tokens)

        logpos = math.log(max(1e-12, min(1.0 - 1e-12, self.pos_prior[tier])))
        logneg = math.log(max(1e-12, min(1.0 - 1e-12, 1.0 - self.pos_prior[tier])))

        lp = self.loglik_pos[tier]
        ln = self.loglik_neg[tier]
        for idx, cnt in hcnt.items():
            logpos += float(lp[idx]) * cnt
            logneg += float(ln[idx]) * cnt

        return _sigmoid(logpos - logneg)


def _find_data_path() -> Optional[str]:
    candidates = [
        os.path.join("resources", "reference_data.csv"),
    ]
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        prob_dir = os.path.dirname(base)
        candidates.append(os.path.join(prob_dir, "resources", "reference_data.csv"))
    except Exception:
        pass

    for p in candidates:
        if os.path.exists(p) and os.path.isfile(p):
            return p
    return None


def _read_csv_rows(path: str, limit: Optional[int] = None) -> Tuple[List[Dict[str, str]], List[str]]:
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for i, row in enumerate(reader):
            rows.append(row)
            if limit is not None and i + 1 >= limit:
                break
    return rows, fieldnames


def _median(xs: List[float]) -> float:
    xs = [x for x in xs if x == x and x > 0]
    if not xs:
        return float("nan")
    xs.sort()
    n = len(xs)
    if n % 2 == 1:
        return xs[n // 2]
    return 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def _infer_tier_models(fieldnames: List[str]) -> Dict[str, str]:
    # Prefer canonical 3-model mapping when present
    canonical = {
        "cheap": "mistralai/mistral-7b-chat",
        "mid": "mistralai/mixtral-8x7b-chat",
        "expensive": "gpt-4-1106-preview",
    }
    if all(m in fieldnames for m in canonical.values()):
        return canonical

    # Fallback: try find exactly 3 oracle labels and map by cost if possible
    # (requires reading rows; handled elsewhere if needed)
    # Final fallback: pick 3 by presence of known model list in order
    known_order = [
        "mistralai/mistral-7b-chat",
        "gpt-3.5-turbo-1106",
        "mistralai/mixtral-8x7b-chat",
        "meta/code-llama-instruct-34b-chat",
        "zero-one-ai/Yi-34B-Chat",
        "WizardLM/WizardLM-13B-V1.2",
        "claude-instant-v1",
        "claude-v1",
        "claude-v2",
        "meta/llama-2-70b-chat",
        "gpt-4-1106-preview",
    ]
    present = [m for m in known_order if m in fieldnames]
    if len(present) >= 3:
        return {"cheap": present[0], "mid": present[1], "expensive": present[2]}

    # As a last resort, pick any 3 non-cost/non-response columns
    model_like = []
    for fn in fieldnames:
        if fn in ("sample_id", "prompt", "eval_name", "oracle_model_to_route_to"):
            continue
        if "|total_cost" in fn or "|model_response" in fn:
            continue
        model_like.append(fn)
    if len(model_like) >= 3:
        return {"cheap": model_like[0], "mid": model_like[1], "expensive": model_like[2]}
    return {}


def _estimate_costs(rows: List[Dict[str, str]], tier_models: Dict[str, str]) -> Dict[str, float]:
    costs = {}
    for tier, model in tier_models.items():
        ccol = model + "|total_cost"
        xs = []
        for r in rows:
            v = _safe_float(r.get(ccol, ""), default=float("nan"))
            if v == v and v > 0:
                xs.append(v)
        med = _median(xs)
        if med == med and med > 0:
            costs[tier] = med
    # Fallback constants if missing
    if "cheap" not in costs:
        costs["cheap"] = 2.0e-5
    if "mid" not in costs:
        costs["mid"] = 7.0e-5
    if "expensive" not in costs:
        costs["expensive"] = 9.0e-4
    return costs


_GLOBAL_ROUTER: Optional[_BinaryNBRouter] = None
_GLOBAL_READY: bool = False


def _get_router() -> Optional[_BinaryNBRouter]:
    global _GLOBAL_ROUTER, _GLOBAL_READY
    if _GLOBAL_READY:
        return _GLOBAL_ROUTER
    _GLOBAL_READY = True

    path = _find_data_path()
    if not path:
        _GLOBAL_ROUTER = None
        return None

    try:
        rows, fieldnames = _read_csv_rows(path)
        if not rows or not fieldnames:
            _GLOBAL_ROUTER = None
            return None

        tier_models = _infer_tier_models(fieldnames)
        if not tier_models or any(t not in tier_models for t in ("cheap", "mid", "expensive")):
            _GLOBAL_ROUTER = None
            return None

        tier_costs = _estimate_costs(rows, tier_models)
        model_cols = dict(tier_models)
        cost_cols = {t: tier_models[t] + "|total_cost" for t in tier_models}

        router = _BinaryNBRouter(dim_pow2=18, alpha=0.5)
        router.train(rows, model_cols=model_cols, cost_cols=cost_cols, cost_est=tier_costs)
        _GLOBAL_ROUTER = router
        return router
    except Exception:
        _GLOBAL_ROUTER = None
        return None


class Solution:
    def solve(self, query: str, eval_name: str, candidate_models: List[str]) -> str:
        if not candidate_models:
            return "cheap"

        cm_set = set(candidate_models)
        # If tiers are different names, just return first valid option
        if not (("cheap" in cm_set) or ("mid" in cm_set) or ("expensive" in cm_set)):
            return candidate_models[0]

        router = _get_router()
        q = query or ""

        if router is None or not router.trained:
            # Simple fallback heuristics
            text = _normalize_text(q).lower()
            if "```" in text or _CODE_HINT_RE.search(text) or "traceback" in text:
                if "mid" in cm_set:
                    return "mid"
                if "expensive" in cm_set:
                    return "expensive"
                return candidate_models[0]
            if len(text) > 900:
                if "mid" in cm_set:
                    return "mid"
                if "expensive" in cm_set:
                    return "expensive"
                return candidate_models[0]
            if _MC_RE.search(text) or _HAS_LETTER_CHOICES_RE.search(text):
                if "cheap" in cm_set:
                    return "cheap"
                return candidate_models[0]
            if "cheap" in cm_set:
                return "cheap"
            return candidate_models[0]

        tokens = _extract_tokens(q, eval_name)
        lam = 150.0

        best_model = None
        best_u = -1e18
        best_cost = float("inf")

        for tier in ("cheap", "mid", "expensive"):
            if tier not in cm_set:
                continue
            p = router.predict_p_correct(tokens, tier)
            c = float(router.cost_est.get(tier, 1e-4))
            u = p - lam * c
            if (u > best_u) or (u == best_u and c < best_cost):
                best_u = u
                best_model = tier
                best_cost = c

        if best_model is None:
            return candidate_models[0]
        return best_model