import os
import csv
import math
import zlib
import re
from functools import lru_cache
import numpy as np

TOKEN_RE = re.compile(r"[a-z0-9]+")

CHEAP_CONCRETE = "mistralai/mistral-7b-chat"
MID_CONCRETE = "mistralai/mixtral-8x7b-chat"
EXP_CONCRETE = "gpt-4-1106-preview"

TIERS = ("cheap", "mid", "expensive")
CONCRETE_MODELS = (CHEAP_CONCRETE, MID_CONCRETE, EXP_CONCRETE)

LAMBDA_COST = 150.0

HASH_DIM = 131072  # power of two
MAX_TOKENS = 160
MAX_BIGRAMS = 50

DEFAULT_PRIOR_CORRECT = np.array([0.62, 0.72, 0.84], dtype=np.float32)
DEFAULT_COST_PER_CHAR = np.array([2.5e-8, 8.0e-8, 1.2e-6], dtype=np.float32)


@lru_cache(maxsize=60000)
def _hash_tok(tok: str):
    h = zlib.crc32(tok.encode("utf-8", errors="ignore")) & 0xFFFFFFFF
    idx = h & (HASH_DIM - 1)
    sign = 1.0 if (h & 0x80000000) == 0 else -1.0
    return idx, sign


def _sigmoid_vec(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, -20.0, 20.0)
    return 1.0 / (1.0 + np.exp(-x))


def _extract_features(text: str, eval_name: str):
    if not text:
        text = ""
    tl = text.lower()
    ev = (eval_name or "").strip().lower()

    feats = {}

    def add(name: str, val: float = 1.0):
        idx, sign = _hash_tok(name)
        feats[idx] = feats.get(idx, 0.0) + sign * val

    # Task indicator
    if ev:
        add("__eval__" + ev, 1.0)
        # also a coarser prefix for tasks like mmlu-*
        if "-" in ev:
            add("__evalp__" + ev.split("-", 1)[0], 1.0)
        if "." in ev:
            add("__evald__" + ev.split(".", 1)[0], 1.0)

    char_len = len(text)
    word_tokens = TOKEN_RE.findall(tl)

    # Unique tokens in first MAX_TOKENS (order-preserving)
    seen = {}
    for tok in word_tokens[:MAX_TOKENS]:
        if tok not in seen:
            seen[tok] = 1

    for tok in seen.keys():
        idx, sign = _hash_tok("w:" + tok)
        feats[idx] = feats.get(idx, 0.0) + sign

    # Bigrams (first MAX_BIGRAMS)
    if len(word_tokens) > 1:
        lim = min(MAX_BIGRAMS, len(word_tokens) - 1)
        for i in range(lim):
            bg = word_tokens[i] + "_" + word_tokens[i + 1]
            idx, sign = _hash_tok("b:" + bg)
            feats[idx] = feats.get(idx, 0.0) + sign

    # Structural/heuristic features
    newline_count = text.count("\n")
    add("__nl_bin__" + str(min(10, newline_count // 3)), 1.0)

    add("__char_bin__" + str(min(16, char_len // 200)), 1.0)
    add("__word_bin__" + str(min(16, len(word_tokens) // 40)), 1.0)

    if "```" in text or "def " in tl or "class " in tl or "import " in tl:
        add("__has_code__", 1.0)

    if ("a)" in tl and "b)" in tl and "c)" in tl) or ("a." in tl and "b." in tl and "c." in tl):
        add("__has_mcq__", 1.0)

    if "step-by-step" in tl or "step by step" in tl or "show your work" in tl:
        add("__asks_steps__", 1.0)

    if "prove" in tl or "deriv" in tl or "rigor" in tl:
        add("__asks_proof__", 1.0)

    digit_count = 0
    op_count = 0
    for ch in text:
        o = ord(ch)
        if 48 <= o <= 57:
            digit_count += 1
        if ch in "+-*/=^":
            op_count += 1
    if digit_count:
        add("__digit_bin__" + str(min(10, digit_count // 10)), 1.0)
    if op_count:
        add("__op_bin__" + str(min(10, op_count // 6)), 1.0)

    # Continuous length features
    add("__charlen__", char_len / 1000.0)
    add("__wordlen__", len(word_tokens) / 200.0)
    add("__nlines__", newline_count / 30.0)

    return list(feats.items()), char_len


def _find_reference_path():
    candidates = [
        "resources/reference_data.csv",
        os.path.join(os.getcwd(), "resources", "reference_data.csv"),
    ]
    try:
        here = os.path.abspath(__file__)
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(here)), "resources", "reference_data.csv"))
        candidates.append(os.path.join(os.path.dirname(here), "resources", "reference_data.csv"))
    except Exception:
        pass
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


class _RouterModel:
    __slots__ = (
        "W",
        "b",
        "prior_overall",
        "prior_by_eval",
        "cost_rate_overall",
        "cost_rate_by_eval",
        "trained",
    )

    def __init__(self):
        self.W = np.zeros((3, HASH_DIM), dtype=np.float32)
        self.b = np.zeros(3, dtype=np.float32)
        self.prior_overall = DEFAULT_PRIOR_CORRECT.copy()
        self.prior_by_eval = {}
        self.cost_rate_overall = DEFAULT_COST_PER_CHAR.copy()
        self.cost_rate_by_eval = {}
        self.trained = False

        path = _find_reference_path()
        if not path:
            return

        try:
            csv.field_size_limit(1 << 28)
        except Exception:
            pass

        try:
            self._train_from_csv(path)
            self.trained = True
        except Exception:
            self.W.fill(0.0)
            self.b.fill(0.0)
            self.prior_overall = DEFAULT_PRIOR_CORRECT.copy()
            self.cost_rate_overall = DEFAULT_COST_PER_CHAR.copy()
            self.prior_by_eval = {}
            self.cost_rate_by_eval = {}
            self.trained = False

    def _train_from_csv(self, path: str):
        # Determine column indices
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)

        col = {name: i for i, name in enumerate(header)}
        prompt_idx = col.get("prompt", None)
        eval_idx = col.get("eval_name", None)

        corr_idx = []
        cost_idx = []
        for m in CONCRETE_MODELS:
            corr_idx.append(col.get(m, None))
            cost_idx.append(col.get(m + "|total_cost", None))

        if prompt_idx is None or eval_idx is None or any(i is None for i in corr_idx) or any(i is None for i in cost_idx):
            raise RuntimeError("Required columns not found in reference_data.csv")

        # First pass: collect priors and cost rates, plus train (epoch 0)
        n_epochs = 2
        lr0 = 0.45
        decay = 2.0e-5
        l2 = 2.0e-6

        # stats
        total_n = 0
        sum_correct = np.zeros(3, dtype=np.float64)
        sum_cost = np.zeros(3, dtype=np.float64)
        sum_chars = 0.0

        eval_stats = {}  # eval -> [n, sum_chars, sum_correct(3), sum_cost(3)]
        step = 0

        for epoch in range(n_epochs):
            with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                reader = csv.reader(f)
                _ = next(reader, None)  # header
                for row in reader:
                    if not row:
                        continue
                    try:
                        prompt = row[prompt_idx]
                        ev = row[eval_idx]
                    except Exception:
                        continue

                    ys = np.zeros(3, dtype=np.float32)
                    cs = np.zeros(3, dtype=np.float32)
                    ok = True
                    for k in range(3):
                        try:
                            yv = row[corr_idx[k]]
                            cv = row[cost_idx[k]]
                            if yv == "" or cv == "":
                                ok = False
                                break
                            ys[k] = float(yv)
                            cs[k] = float(cv)
                        except Exception:
                            ok = False
                            break
                    if not ok:
                        continue

                    feats, char_len = _extract_features(prompt, ev)

                    # Train correctness logits
                    logits = self.b.astype(np.float32, copy=True)
                    for idx, val in feats:
                        logits += self.W[:, idx] * np.float32(val)
                    probs = _sigmoid_vec(logits)
                    grads = probs - ys

                    lr = lr0 / (1.0 + decay * step)
                    step += 1

                    self.b -= np.float32(lr) * grads.astype(np.float32)
                    lr_f = np.float32(lr)
                    l2_f = np.float32(l2)

                    for idx, val in feats:
                        v = np.float32(val)
                        wcol = self.W[:, idx]
                        self.W[:, idx] = wcol - lr_f * (grads.astype(np.float32) * v + l2_f * wcol)

                    # stats only on first epoch
                    if epoch == 0:
                        total_n += 1
                        sum_correct += ys.astype(np.float64)
                        sum_cost += cs.astype(np.float64)
                        sum_chars += float(max(1, char_len))

                        key = (ev or "").strip().lower()
                        st = eval_stats.get(key)
                        if st is None:
                            st = [0, 0.0, np.zeros(3, dtype=np.float64), np.zeros(3, dtype=np.float64)]
                            eval_stats[key] = st
                        st[0] += 1
                        st[1] += float(max(1, char_len))
                        st[2] += ys.astype(np.float64)
                        st[3] += cs.astype(np.float64)

        if total_n > 0:
            self.prior_overall = (sum_correct / float(total_n)).astype(np.float32)
            # global cost rate per char (guard)
            denom = max(1.0, sum_chars)
            self.cost_rate_overall = (sum_cost / denom).astype(np.float32)
            self.cost_rate_overall = np.maximum(self.cost_rate_overall, 0.0)

        # per-eval priors and cost rates
        self.prior_by_eval = {}
        self.cost_rate_by_eval = {}
        for k, st in eval_stats.items():
            n, schars, scorr, scost = st
            if n <= 0:
                continue
            prior = (scorr / float(n)).astype(np.float32)
            denom = max(1.0, schars)
            rate = (scost / denom).astype(np.float32)
            rate = np.maximum(rate, 0.0)
            self.prior_by_eval[k] = prior
            self.cost_rate_by_eval[k] = rate

    def choose(self, query: str, eval_name: str):
        feats, char_len = _extract_features(query, eval_name)

        logits = self.b.astype(np.float32, copy=True)
        for idx, val in feats:
            logits += self.W[:, idx] * np.float32(val)
        probs = _sigmoid_vec(logits).astype(np.float32)

        ev = (eval_name or "").strip().lower()
        prior = self.prior_by_eval.get(ev, self.prior_overall)
        # Blend to reduce overconfidence and leverage task identity
        probs = 0.72 * probs + 0.28 * prior

        rate = self.cost_rate_by_eval.get(ev, self.cost_rate_overall)
        cost_est = rate * float(max(1, char_len))

        reward = probs.astype(np.float64) - (LAMBDA_COST * cost_est.astype(np.float64))
        best = int(np.argmax(reward))

        # Small heuristic safety for code-generation tasks
        tl = (query or "").lower()
        is_code_like = ("def " in tl) or ("class " in tl) or ("```" in (query or "")) or ("write a function" in tl)
        ev_lower = ev
        if is_code_like and best == 0 and (("mbpp" in ev_lower) or ("humaneval" in ev_lower) or ("code" in ev_lower)):
            best = 1

        return TIERS[best]


_GLOBAL_MODEL = None


class Solution:
    def __init__(self):
        global _GLOBAL_MODEL
        if _GLOBAL_MODEL is None:
            _GLOBAL_MODEL = _RouterModel()
        self._model = _GLOBAL_MODEL

    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        if not candidate_models:
            return "cheap"
        cand_map = {}
        for c in candidate_models:
            if isinstance(c, str):
                cand_map[c.lower()] = c

        pred = self._model.choose(query or "", eval_name or "")

        if pred in cand_map:
            return cand_map[pred]

        # Fallback: nearest by tier order among available
        avail = []
        for t in TIERS:
            if t in cand_map:
                avail.append(t)
        if not avail:
            return candidate_models[0]

        target_idx = TIERS.index(pred)
        best_t = min(avail, key=lambda t: abs(TIERS.index(t) - target_idx))
        return cand_map[best_t]