import os
import re
import math
import numpy as np
from collections import Counter, defaultdict

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


_LAMBDA = 150.0


_WORD_RE = re.compile(r"[a-zA-Z_]{2,}|\d+|[^\s]", re.UNICODE)
_MC_RE = re.compile(r"(?:^|\n|\r)\s*(?:[A-Da-d][\)\.]|[A-Da-d]\s*:)\s+")
_CODE_HINT_RE = re.compile(
    r"```|(?:^|\n)\s*(?:def|class)\s+|import\s+\w+|from\s+\w+\s+import|"
    r"\bpython\b|\bjavascript\b|\bjava\b|\bc\+\+\b|\bsql\b|\bregex\b|\bstdin\b|\bstdout\b",
    re.IGNORECASE,
)
_MATH_HINT_RE = re.compile(
    r"\b(?:prove|lemma|theorem|corollary|integral|derivative|gradient|matrix|eigen|"
    r"probability|expected value|variance|bayes|logarithm|quadratic|polynomial)\b|"
    r"[∑∫√π≤≥≠≈]|\\frac|\\sum|\\int|\\sqrt|\^",
    re.IGNORECASE,
)


def _family_eval(eval_name: str) -> str:
    e = (eval_name or "").lower()
    if not e:
        return ""
    if e.startswith("mmlu"):
        return "mmlu"
    if "hellaswag" in e:
        return "hellaswag"
    if "gsm" in e or "math" in e or "arithmetic" in e:
        return "math"
    if "mbpp" in e or "humaneval" in e or "code" in e:
        return "code"
    if "arc" in e:
        return "arc"
    if "truthfulqa" in e:
        return "truthfulqa"
    if "winogrande" in e:
        return "winogrande"
    return e.split("-")[0]


def _len_bucket(n: int) -> str:
    if n < 80:
        return "0"
    if n < 200:
        return "1"
    if n < 500:
        return "2"
    if n < 1000:
        return "3"
    if n < 2000:
        return "4"
    if n < 4000:
        return "5"
    return "6"


def _nl_bucket(n: int) -> str:
    if n < 1:
        return "0"
    if n < 3:
        return "1"
    if n < 8:
        return "2"
    if n < 20:
        return "3"
    return "4"


class _HashedNB:
    __slots__ = (
        "dim",
        "mask",
        "alpha",
        "C",
        "log_prob",
        "log_prior",
        "eval_log_prior",
        "trained",
        "cost_median",
    )

    def __init__(self, dim: int = 1 << 17, alpha: float = 0.5, num_classes: int = 3):
        self.dim = int(dim)
        if self.dim & (self.dim - 1) != 0:
            p = 1
            while p < self.dim:
                p <<= 1
            self.dim = p
        self.mask = self.dim - 1
        self.alpha = float(alpha)
        self.C = int(num_classes)
        self.log_prob = None
        self.log_prior = None
        self.eval_log_prior = {}
        self.trained = False
        self.cost_median = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    def _tokens(self, text: str, eval_name: str) -> list[str]:
        if text is None:
            text = ""
        if not isinstance(text, str):
            text = str(text)
        t = text.replace("\\n", "\n")
        lower = t.lower()
        toks = []

        e = (eval_name or "").lower()
        if e:
            toks.append("__eval__" + e)
            fam = _family_eval(e)
            if fam and fam != e:
                toks.append("__evalfam__" + fam)

        n_chars = len(t)
        toks.append("__len__" + _len_bucket(n_chars))
        n_nl = t.count("\n")
        toks.append("__nl__" + _nl_bucket(n_nl))

        if _MC_RE.search(t):
            toks.append("__mcq__")
        if _CODE_HINT_RE.search(t):
            toks.append("__code__")
        if _MATH_HINT_RE.search(t):
            toks.append("__math__")
        if "step by step" in lower or "chain-of-thought" in lower or "show your work" in lower:
            toks.append("__cot__")
        if "json" in lower:
            toks.append("__json__")
        if "sql" in lower:
            toks.append("__sql__")

        base = _WORD_RE.findall(lower)
        if len(base) > 700:
            base = base[:700]
        toks.extend(base)

        bigrams = []
        prev = None
        added = 0
        for tok in base:
            if prev is not None:
                if prev.isalpha() and tok.isalpha():
                    bigrams.append(prev + "_" + tok)
                    added += 1
                    if added >= 220:
                        break
            prev = tok
        toks.extend(bigrams)
        return toks

    def _feats(self, text: str, eval_name: str) -> Counter:
        toks = self._tokens(text, eval_name)
        mask = self.mask
        idxs = [hash(tok) & mask for tok in toks]
        return Counter(idxs)

    def fit(self, texts, eval_names, labels, eval_label_counts=None, cost_median=None):
        n = len(texts)
        C = self.C
        D = self.dim
        alpha = self.alpha

        counts = np.zeros((C, D), dtype=np.uint32)
        total = np.zeros(C, dtype=np.float64)
        docc = np.zeros(C, dtype=np.uint32)

        if eval_label_counts is None:
            eval_label_counts = defaultdict(lambda: np.zeros(C, dtype=np.uint32))

        for i in range(n):
            c = int(labels[i])
            if c < 0 or c >= C:
                continue
            docc[c] += 1
            feats = self._feats(texts[i], eval_names[i])
            if not feats:
                continue
            idxs = np.fromiter(feats.keys(), dtype=np.int64, count=len(feats))
            vals = np.fromiter(feats.values(), dtype=np.int64, count=len(feats))
            np.add.at(counts[c], idxs, vals)
            total[c] += float(vals.sum())
            ev = (eval_names[i] or "").lower()
            if ev:
                eval_label_counts[ev][c] += 1

        doc_total = float(max(1, int(docc.sum())))
        self.log_prior = (np.log(docc.astype(np.float64) + 1e-9) - math.log(doc_total)).astype(np.float32)

        denom = total + alpha * D
        denom_log = np.log(denom).astype(np.float32)
        counts_f = counts.astype(np.float32)
        self.log_prob = (np.log(counts_f + alpha, dtype=np.float32) - denom_log[:, None]).astype(np.float32)

        self.eval_log_prior = {}
        for ev, cnts in eval_label_counts.items():
            s = float(cnts.sum())
            if s <= 0:
                continue
            lp = (np.log(cnts.astype(np.float64) + 0.5) - math.log(s + 0.5 * C)).astype(np.float32)
            self.eval_log_prior[ev] = lp

        if cost_median is not None:
            cm = np.array(cost_median, dtype=np.float32)
            if cm.shape == (C,):
                self.cost_median = cm

        self.trained = True

    def predict_scores(self, text: str, eval_name: str) -> np.ndarray:
        if not self.trained:
            return np.zeros(self.C, dtype=np.float32)
        feats = self._feats(text, eval_name)
        scores = self.log_prior.astype(np.float32).copy()
        ev = (eval_name or "").lower()
        lp = self.eval_log_prior.get(ev)
        if lp is not None:
            scores += 0.55 * lp

        log_prob = self.log_prob
        for idx, cnt in feats.items():
            scores += (float(cnt) * log_prob[:, idx])
        return scores


def _try_find_data_path() -> str:
    candidates = []
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(here, "resources", "reference_data.csv"))
        candidates.append(os.path.join(os.path.dirname(here), "resources", "reference_data.csv"))
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(here)), "resources", "reference_data.csv"))
    except Exception:
        pass
    candidates.append(os.path.join("resources", "reference_data.csv"))
    candidates.append("reference_data.csv")
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return ""


def _infer_tier_models_from_df(df) -> list[str]:
    preferred = ["mistralai/mistral-7b-chat", "mistralai/mixtral-8x7b-chat", "gpt-4-1106-preview"]
    cols = set(df.columns)
    ok = True
    for m in preferred:
        if m not in cols or (m + "|total_cost") not in cols:
            ok = False
            break
    if ok:
        return preferred

    base_models = []
    for c in df.columns:
        if c.endswith("|total_cost"):
            base = c[:-len("|total_cost")]
            if base in cols:
                base_models.append(base)
    base_models = sorted(set(base_models))
    if len(base_models) < 3:
        return preferred

    med_costs = []
    for m in base_models:
        try:
            arr = df[m + "|total_cost"].to_numpy(dtype=np.float64, copy=False)
            arr = np.nan_to_num(arr, nan=np.inf, posinf=np.inf, neginf=np.inf)
            mc = float(np.median(arr[np.isfinite(arr)])) if np.isfinite(arr).any() else float("inf")
        except Exception:
            mc = float("inf")
        med_costs.append((mc, m))
    med_costs.sort(key=lambda x: x[0])

    cheap = med_costs[0][1]
    expensive = med_costs[-1][1]
    target = math.sqrt(max(med_costs[0][0], 1e-12) * max(med_costs[-1][0], 1e-12))
    mid = None
    best = float("inf")
    for mc, m in med_costs[1:-1]:
        d = abs(mc - target)
        if d < best:
            best = d
            mid = m
    if mid is None:
        mid = med_costs[len(med_costs) // 2][1]
    return [cheap, mid, expensive]


def _compute_median_costs(df, tier_models: list[str]) -> list[float]:
    out = []
    for m in tier_models:
        col = m + "|total_cost"
        if col in df.columns:
            arr = df[col].to_numpy(dtype=np.float64, copy=False)
            arr = np.nan_to_num(arr, nan=np.inf, posinf=np.inf, neginf=np.inf)
            if np.isfinite(arr).any():
                out.append(float(np.median(arr[np.isfinite(arr)])))
            else:
                out.append(1.0)
        else:
            out.append(1.0)
    return out


def _train_from_reference():
    data_path = _try_find_data_path()
    if not data_path or pd is None:
        return None

    try:
        df = pd.read_csv(data_path)
    except Exception:
        return None

    if "prompt" not in df.columns or "eval_name" not in df.columns:
        return None

    tier_models = _infer_tier_models_from_df(df)
    for m in tier_models:
        if m not in df.columns or (m + "|total_cost") not in df.columns:
            return None

    corr_cols = tier_models
    cost_cols = [m + "|total_cost" for m in tier_models]

    corr = []
    cost = []
    for c in corr_cols:
        a = df[c].to_numpy(dtype=np.float32, copy=False)
        a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
        corr.append(a)
    for c in cost_cols:
        a = df[c].to_numpy(dtype=np.float32, copy=False)
        a = np.nan_to_num(a, nan=1e3, posinf=1e3, neginf=1e3)
        cost.append(a)

    corr_mat = np.stack(corr, axis=1)
    cost_mat = np.stack(cost, axis=1)
    util = corr_mat - (_LAMBDA * cost_mat)
    labels = util.argmax(axis=1).astype(np.int8)

    texts = df["prompt"].astype(str).to_numpy()
    evals = df["eval_name"].astype(str).to_numpy()

    max_train = 60000
    if len(texts) > max_train:
        idx = np.random.RandomState(0).choice(len(texts), size=max_train, replace=False)
        texts = texts[idx]
        evals = evals[idx]
        labels = labels[idx]

    eval_label_counts = defaultdict(lambda: np.zeros(3, dtype=np.uint32))
    cost_median = _compute_median_costs(df, tier_models)

    model = _HashedNB(dim=1 << 17, alpha=0.6, num_classes=3)
    model.fit(texts, evals, labels, eval_label_counts=eval_label_counts, cost_median=cost_median)
    return model


class Solution:
    _model = None
    _ready = False

    def __init__(self):
        if not Solution._ready:
            Solution._model = _train_from_reference()
            Solution._ready = True

    def _fallback(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        if not candidate_models:
            return ""
        q = query if isinstance(query, str) else str(query)
        e = (eval_name or "").lower()
        ql = q.lower()
        has_code = bool(_CODE_HINT_RE.search(q))
        has_math = bool(_MATH_HINT_RE.search(q))
        has_mcq = bool(_MC_RE.search(q))
        n = len(q)

        want = "cheap"
        if has_code or "mbpp" in e or "humaneval" in e:
            want = "mid"
        elif has_math or ("mmlu" in e and not has_mcq and n > 700):
            want = "mid"
        elif n > 2500:
            want = "mid"
        elif has_mcq and n < 700:
            want = "cheap"
        elif "write" in ql and "function" in ql:
            want = "mid"

        for c in candidate_models:
            if c.lower() == want:
                return c
        return candidate_models[0]

    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        if not candidate_models:
            return ""

        model = Solution._model
        if model is None or not getattr(model, "trained", False):
            return self._fallback(query, eval_name, candidate_models)

        cand_to_cls = {}
        for c in candidate_models:
            cl = c.lower()
            if "cheap" in cl:
                cand_to_cls[c] = 0
            elif "mid" in cl:
                cand_to_cls[c] = 1
            elif "exp" in cl:
                cand_to_cls[c] = 2

        if not cand_to_cls:
            return candidate_models[0]

        scores = model.predict_scores(query, eval_name)

        allowed = sorted(set(cand_to_cls.values()))
        allowed_scores = [(cls, float(scores[cls])) for cls in allowed]
        allowed_scores.sort(key=lambda x: x[1], reverse=True)
        best_cls, best_s = allowed_scores[0]
        second_s = allowed_scores[1][1] if len(allowed_scores) > 1 else -1e30

        if best_cls == 2 and 1 in allowed:
            if (best_s - second_s) < 1.15:
                best_cls = 1
        if best_cls == 1 and 0 in allowed:
            if (best_s - second_s) < 0.65:
                best_cls = 0

        for c in candidate_models:
            if cand_to_cls.get(c, -1) == best_cls:
                return c

        return candidate_models[0]