import os
import re
import math
import zlib
from typing import List, Tuple, Dict, Optional

import numpy as np

try:
    import pandas as pd
except Exception:
    pd = None


class _HashCache:
    __slots__ = ("D", "mask", "max_size", "cache")

    def __init__(self, D: int, max_size: int = 50000):
        self.D = int(D)
        self.mask = self.D - 1
        self.max_size = int(max_size)
        self.cache: Dict[str, int] = {}

    def idx(self, tok: str) -> int:
        c = self.cache.get(tok)
        if c is not None:
            return c
        v = zlib.crc32(tok.encode("utf-8")) & self.mask
        if len(self.cache) >= self.max_size:
            self.cache.clear()
        self.cache[tok] = v
        return v


class _BinaryNB:
    __slots__ = ("D", "alpha", "counts", "total", "n", "loglik", "logprior")

    def __init__(self, D: int, alpha: float = 0.5):
        self.D = int(D)
        self.alpha = float(alpha)
        self.counts = np.zeros((2, self.D), dtype=np.float32)
        self.total = np.zeros(2, dtype=np.float64)
        self.n = np.zeros(2, dtype=np.int64)
        self.loglik: Optional[np.ndarray] = None
        self.logprior: Optional[np.ndarray] = None

    def update(self, idxs: List[int], cnts: List[int], y: int) -> None:
        y = 1 if y else 0
        self.n[y] += 1
        row = self.counts[y]
        tot_add = 0.0
        for i, c in zip(idxs, cnts):
            row[i] += float(c)
            tot_add += float(c)
        self.total[y] += tot_add

    def finalize(self) -> None:
        nsum = int(self.n[0] + self.n[1])
        if nsum <= 0:
            self.loglik = np.zeros((2, self.D), dtype=np.float32)
            self.logprior = np.array([math.log(0.5), math.log(0.5)], dtype=np.float32)
            return

        denom0 = float(self.total[0] + self.alpha * self.D)
        denom1 = float(self.total[1] + self.alpha * self.D)
        ll0 = np.log((self.counts[0] + self.alpha) / denom0)
        ll1 = np.log((self.counts[1] + self.alpha) / denom1)
        self.loglik = np.vstack([ll0, ll1]).astype(np.float32, copy=False)

        p0 = float(self.n[0]) / nsum
        p1 = float(self.n[1]) / nsum
        p0 = max(p0, 1e-12)
        p1 = max(p1, 1e-12)
        self.logprior = np.array([math.log(p0), math.log(p1)], dtype=np.float32)

    def p1(self, idxs: List[int], cnts: List[int]) -> float:
        if self.loglik is None or self.logprior is None:
            return 0.5
        ll = self.loglik
        lp = self.logprior
        s0 = float(lp[0])
        s1 = float(lp[1])
        ll0 = ll[0]
        ll1 = ll[1]
        for i, c in zip(idxs, cnts):
            fc = float(c)
            s0 += fc * float(ll0[i])
            s1 += fc * float(ll1[i])
        d = s0 - s1
        if d > 60.0:
            return 0.0
        if d < -60.0:
            return 1.0
        return 1.0 / (1.0 + math.exp(d))


class _FeatureExtractor:
    __slots__ = ("D", "hasher", "word_re", "mc_re")

    def __init__(self, D: int, hasher: _HashCache):
        self.D = int(D)
        self.hasher = hasher
        self.word_re = re.compile(r"[A-Za-z_][A-Za-z_0-9]{1,}|[A-Za-z_]|[0-9]+|==|!=|<=|>=|->|:=|\+\+|--")
        self.mc_re = re.compile(r"(^|\n)\s*([A-D])\s*[\)\.:\-]\s+", re.IGNORECASE)

    def _meta_tokens(self, q: str, eval_name: str) -> List[str]:
        toks: List[str] = []
        if eval_name:
            toks.append(f"__EVAL__{eval_name.lower()}")

        nchar = len(q)
        nline = q.count("\n") + 1
        nbucket = min(16, int(math.log2(nchar + 1))) if nchar > 0 else 0
        lbucket = min(10, int(math.log2(nline + 1))) if nline > 0 else 0
        toks.append(f"__CHARS__{nbucket}")
        toks.append(f"__LINES__{lbucket}")

        ql = q.lower()
        has_code = ("def " in ql) or ("class " in ql) or ("import " in ql) or ("```" in q) or ("#include" in ql) or ("public static" in ql)
        has_math = any(op in q for op in ["=", "+", "-", "*", "/", "^"]) and any(ch.isdigit() for ch in q)
        has_mc = bool(self.mc_re.search(q)) or ("choices" in ql and ("a)" in ql or "b)" in ql or "c)" in ql))
        has_sql = ("select " in ql and " from " in ql) or (" join " in ql)
        has_json = ("{" in q and "}" in q and ":" in q) or ("[" in q and "]" in q and ":" in q)

        if has_code:
            toks.append("__HAS_CODE__")
        if has_math:
            toks.append("__HAS_MATH__")
        if has_mc:
            toks.append("__HAS_MC__")
        if has_sql:
            toks.append("__HAS_SQL__")
        if has_json:
            toks.append("__HAS_JSON__")

        if "prove" in ql or "theorem" in ql or "derive" in ql:
            toks.append("__HAS_PROOF__")
        if "step by step" in ql or "explain" in ql or "reason" in ql:
            toks.append("__WANTS_REASONING__")
        if "optimize" in ql or "complexity" in ql or "big-o" in ql or "time complexity" in ql:
            toks.append("__CS_COMPLEXITY__")

        return toks

    def featurize(self, q: str, eval_name: str) -> Tuple[List[int], List[int]]:
        if not isinstance(q, str):
            q = str(q)

        tokens = self.word_re.findall(q.lower())
        if len(tokens) > 500:
            tokens = tokens[:250] + tokens[-250:]

        meta = self._meta_tokens(q, eval_name)
        tokens.extend(meta)

        # Add a few bigrams for early tokens
        max_big = min(80, len(tokens) - len(meta))
        for i in range(max_big - 1):
            a = tokens[i]
            b = tokens[i + 1]
            if a and b and a[0].isalpha() and b[0].isalpha():
                tokens.append(a + "__" + b)

        # Count & cap
        counts: Dict[int, int] = {}
        h = self.hasher
        for t in tokens:
            if not t:
                continue
            idx = h.idx(t)
            prev = counts.get(idx)
            if prev is None:
                counts[idx] = 1
            else:
                if prev < 4:
                    counts[idx] = prev + 1

        if not counts:
            return [], []

        idxs = list(counts.keys())
        cnts = [counts[i] for i in idxs]
        return idxs, cnts


def _safe_mean(arr: np.ndarray) -> float:
    if arr.size == 0:
        return float("nan")
    return float(np.nanmean(arr))


def _safe_median(arr: np.ndarray) -> float:
    if arr.size == 0:
        return float("nan")
    return float(np.nanmedian(arr))


def _linear_fit(xs: np.ndarray, ys: np.ndarray) -> Tuple[float, float]:
    if xs.size < 2:
        return float(np.nan), float(np.nan)
    xm = float(xs.mean())
    ym = float(ys.mean())
    vx = float(((xs - xm) ** 2).mean())
    if vx <= 1e-18:
        return ym, 0.0
    cov = float(((xs - xm) * (ys - ym)).mean())
    b = cov / vx
    if not np.isfinite(b) or b < 0.0:
        b = 0.0
    a = ym - b * xm
    if not np.isfinite(a):
        a = ym
    return a, b


class Solution:
    def __init__(self):
        self._lambda = 150.0
        self._tiers = ["cheap", "mid", "expensive"]
        self._D = 1 << 16
        self._hasher = _HashCache(self._D)
        self._fe = _FeatureExtractor(self._D, self._hasher)

        self._ready = False

        # Per-tier binary NB: predicts correctness probability for that tier
        self._nb: Dict[str, _BinaryNB] = {t: _BinaryNB(self._D, alpha=0.5) for t in self._tiers}

        # Cost model per tier: cost ~= a + b * len(query)
        self._cost_a: Dict[str, float] = {t: 0.0 for t in self._tiers}
        self._cost_b: Dict[str, float] = {t: 0.0 for t in self._tiers}
        self._cost_min: Dict[str, float] = {t: 0.0 for t in self._tiers}

        self._tier_to_concrete: Dict[str, str] = {}
        self._concrete_models: List[str] = []

        try:
            self._train_from_reference()
            self._ready = True
        except Exception:
            self._ready = False

    def _read_reference_df(self):
        paths = []
        paths.append(os.path.join("resources", "reference_data.csv"))
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            problem_dir = os.path.dirname(here)
            paths.append(os.path.join(problem_dir, "resources", "reference_data.csv"))
        except Exception:
            pass

        data_path = None
        for p in paths:
            if os.path.exists(p):
                data_path = p
                break
        if data_path is None:
            return None

        if pd is not None:
            return pd.read_csv(data_path)
        return None

    def _infer_tier_models(self, df) -> Dict[str, str]:
        preferred = {
            "cheap": "mistralai/mistral-7b-chat",
            "mid": "mistralai/mixtral-8x7b-chat",
            "expensive": "gpt-4-1106-preview",
        }
        ok = True
        for t, m in preferred.items():
            if m not in df.columns or f"{m}|total_cost" not in df.columns:
                ok = False
                break
        if ok:
            return dict(preferred)

        cost_cols = [c for c in df.columns if isinstance(c, str) and c.endswith("|total_cost")]
        models = []
        for c in cost_cols:
            m = c[: -len("|total_cost")]
            if m in df.columns:
                models.append(m)
        models = list(dict.fromkeys(models))
        if not models:
            return dict(preferred)

        stats = []
        for m in models:
            ccol = f"{m}|total_cost"
            y = df[m].to_numpy(dtype=np.float32, copy=False)
            x = df[ccol].to_numpy(dtype=np.float64, copy=False)
            mask = np.isfinite(x) & (x > 0.0) & np.isfinite(y)
            n = int(mask.sum())
            if n < 50:
                continue
            cm = _safe_mean(x[mask])
            cmed = _safe_median(x[mask])
            am = _safe_mean(y[mask])
            if not (np.isfinite(cm) and np.isfinite(cmed) and np.isfinite(am)):
                continue
            stats.append((m, float(am), float(cm), float(cmed), n))

        if len(stats) < 3:
            # fallback: pick three by cost median among whatever exists
            stats = []
            for m in models:
                ccol = f"{m}|total_cost"
                if ccol not in df.columns or m not in df.columns:
                    continue
                x = df[ccol].to_numpy(dtype=np.float64, copy=False)
                mask = np.isfinite(x) & (x > 0.0)
                n = int(mask.sum())
                if n < 10:
                    continue
                cmed = _safe_median(x[mask])
                stats.append((m, 0.0, float(cmed), float(cmed), n))
            stats.sort(key=lambda z: z[3])
            if len(stats) >= 3:
                cheap_m = stats[0][0]
                mid_m = stats[len(stats) // 2][0]
                exp_m = stats[-1][0]
                return {"cheap": cheap_m, "mid": mid_m, "expensive": exp_m}
            return dict(preferred)

        # cheap = lowest cost median
        stats_sorted_cost = sorted(stats, key=lambda z: z[3])
        cheap_m = stats_sorted_cost[0][0]
        cheap_c = stats_sorted_cost[0][3]

        # expensive = highest mean accuracy (tie-breaker: higher cost median)
        stats_sorted_acc = sorted(stats, key=lambda z: (z[1], z[3]))
        expensive_m = stats_sorted_acc[-1][0]
        expensive_c = stats_sorted_acc[-1][3]

        # mid = maximize average reward among moderate cost range
        low = cheap_c * 2.0
        high = expensive_c / 4.0 if expensive_c > 0 else float("inf")
        mid_cands = []
        for (m, am, cm, cmed, n) in stats:
            if m == cheap_m or m == expensive_m:
                continue
            if not (cmed >= low and cmed <= high):
                continue
            reward = float(am - self._lambda * cm)
            mid_cands.append((reward, am, cmed, m))
        if mid_cands:
            mid_cands.sort()
            mid_m = mid_cands[-1][3]
        else:
            # pick model with median cost between cheap and expensive
            stats_mid = [z for z in stats_sorted_cost if z[0] not in (cheap_m, expensive_m)]
            if stats_mid:
                mid_m = stats_mid[len(stats_mid) // 2][0]
            else:
                mid_m = cheap_m

        # Ensure distinct
        if mid_m == cheap_m:
            for z in stats_sorted_cost[1:]:
                if z[0] != expensive_m:
                    mid_m = z[0]
                    break
        if expensive_m == cheap_m:
            expensive_m = stats_sorted_cost[-1][0]
        if expensive_m == mid_m:
            expensive_m = stats_sorted_cost[-1][0]

        return {"cheap": cheap_m, "mid": mid_m, "expensive": expensive_m}

    def _train_from_reference(self) -> None:
        df = self._read_reference_df()
        if df is None or len(df) == 0:
            raise RuntimeError("reference_data.csv not found or empty")

        self._tier_to_concrete = self._infer_tier_models(df)
        self._concrete_models = [self._tier_to_concrete[t] for t in self._tiers]

        # Prepare cost fits
        xs_by_tier: Dict[str, List[float]] = {t: [] for t in self._tiers}
        ys_by_tier: Dict[str, List[float]] = {t: [] for t in self._tiers}

        prompts = df["prompt"].astype(str).tolist()
        evals = df["eval_name"].astype(str).tolist()

        # Speed: fetch correctness and costs as numpy arrays per tier
        corr_arr: Dict[str, np.ndarray] = {}
        cost_arr: Dict[str, np.ndarray] = {}
        for t in self._tiers:
            m = self._tier_to_concrete[t]
            corr_arr[t] = df[m].to_numpy(dtype=np.float32, copy=False) if m in df.columns else np.full(len(df), np.nan, dtype=np.float32)
            ccol = f"{m}|total_cost"
            cost_arr[t] = df[ccol].to_numpy(dtype=np.float64, copy=False) if ccol in df.columns else np.full(len(df), np.nan, dtype=np.float64)

        for i, (q, en) in enumerate(zip(prompts, evals)):
            if not q:
                continue
            idxs, cnts = self._fe.featurize(q, en)

            if idxs:
                for t in self._tiers:
                    yv = corr_arr[t][i]
                    if np.isfinite(yv):
                        self._nb[t].update(idxs, cnts, 1 if yv >= 0.5 else 0)

            nchar = float(len(q))
            for t in self._tiers:
                cv = cost_arr[t][i]
                if np.isfinite(cv) and cv > 0.0:
                    xs_by_tier[t].append(nchar)
                    ys_by_tier[t].append(float(cv))

        for t in self._tiers:
            self._nb[t].finalize()

        for t in self._tiers:
            ys = np.array(ys_by_tier[t], dtype=np.float64)
            xs = np.array(xs_by_tier[t], dtype=np.float64)
            if ys.size >= 10:
                a, b = _linear_fit(xs, ys)
                if not np.isfinite(a):
                    a = float(np.nanmedian(ys))
                if not np.isfinite(b) or b < 0.0:
                    b = 0.0
                self._cost_a[t] = float(a)
                self._cost_b[t] = float(b)
                self._cost_min[t] = float(np.nanpercentile(ys, 5.0))
            elif ys.size > 0:
                med = float(np.nanmedian(ys))
                self._cost_a[t] = med
                self._cost_b[t] = 0.0
                self._cost_min[t] = max(0.0, float(np.nanmin(ys)))
            else:
                # fallback guesses
                self._cost_a[t] = 0.00005 if t == "mid" else (0.0009 if t == "expensive" else 0.00002)
                self._cost_b[t] = 0.0
                self._cost_min[t] = 0.0

    def _heuristic_fallback(self, query: str, eval_name: str, candidate_models: List[str]) -> str:
        if not candidate_models:
            return "cheap"
        cmset = set(candidate_models)
        ql = (query or "").lower()
        en = (eval_name or "").lower()

        if ("mbpp" in en) or ("code" in en) or ("def " in ql) or ("class " in ql) or ("```" in query):
            if "mid" in cmset:
                return "mid"
            if "expensive" in cmset:
                return "expensive"
            return candidate_models[0]

        if len(query or "") > 900 or ("prove" in ql) or ("derive" in ql) or ("theorem" in ql):
            if "expensive" in cmset:
                return "expensive"
            if "mid" in cmset:
                return "mid"
            return candidate_models[0]

        if "cheap" in cmset:
            return "cheap"
        return candidate_models[0]

    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        if not candidate_models:
            return "cheap"

        cmset = set(candidate_models)
        if not self._ready:
            return self._heuristic_fallback(query, eval_name, candidate_models)

        idxs, cnts = self._fe.featurize(query or "", eval_name or "")
        qlen = float(len(query or ""))

        best_model = None
        best_score = -1e100

        for t in self._tiers:
            if t not in cmset:
                continue
            p = self._nb[t].p1(idxs, cnts)
            cost = self._cost_a[t] + self._cost_b[t] * qlen
            if cost < self._cost_min[t]:
                cost = self._cost_min[t]
            if cost < 0.0 or not np.isfinite(cost):
                cost = max(0.0, self._cost_min[t])
            score = float(p - self._lambda * cost)
            if score > best_score:
                best_score = score
                best_model = t

        if best_model is not None:
            return best_model

        # If none of the known tiers are available, return a valid candidate
        return candidate_models[0]