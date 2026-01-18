import os
import re
from typing import List
import numpy as np

try:
    import pandas as pd
except Exception:  # In case pandas is not available (should not happen)
    pd = None

# Global configuration
_VOCAB_SIZE = 50000
_ALPHA = 1.0
_ALPHA_PRIOR = 1.0
_LAMBDA_COST = 150.0

_CLASS_LABELS = ["cheap", "mid", "expensive"]
_LABEL_TO_INDEX = {label: i for i, label in enumerate(_CLASS_LABELS)}
_INDEX_TO_LABEL = {i: label for i, label in enumerate(_CLASS_LABELS)}
_NUM_CLASSES = len(_CLASS_LABELS)

# Mapping from routing tier to concrete model in reference data
_TIER_TO_MODEL = {
    "cheap": "mistralai/mistral-7b-chat",
    "mid": "mistralai/mixtral-8x7b-chat",
    "expensive": "gpt-4-1106-preview",
}

# Globals for the trained model
_IS_INITIALIZED = False
_MODEL_AVAILABLE = False
_GLOBAL_LOG_PRIOR = None  # shape: (C,)
_EVAL_LOG_PRIORS = {}  # eval_name (str) -> np.ndarray shape (C,)
_COND_LOG_PROBS = None  # shape: (C, V)

_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")


def _tokenize(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.lower()
    tokens = _TOKEN_SPLIT_RE.split(text)
    tokens = [t for t in tokens if t]
    if len(tokens) > 256:
        tokens = tokens[:256]
    return tokens


def _find_data_path():
    candidates = []

    try:
        cwd = os.getcwd()
        candidates.append(os.path.join(cwd, "resources", "reference_data.csv"))
    except Exception:
        pass

    try:
        this_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(this_dir, "resources", "reference_data.csv"))
        parent = os.path.dirname(this_dir)
        candidates.append(os.path.join(parent, "resources", "reference_data.csv"))
        grandparent = os.path.dirname(parent)
        candidates.append(os.path.join(grandparent, "resources", "reference_data.csv"))
    except Exception:
        pass

    candidates.append("resources/reference_data.csv")

    seen = set()
    unique_candidates = []
    for p in candidates:
        if p not in seen:
            seen.add(p)
            unique_candidates.append(p)

    for path in unique_candidates:
        if os.path.exists(path):
            return path
    return unique_candidates[0]


def _initialize_model():
    global _IS_INITIALIZED, _MODEL_AVAILABLE
    global _GLOBAL_LOG_PRIOR, _EVAL_LOG_PRIORS, _COND_LOG_PROBS

    if _IS_INITIALIZED:
        return

    _MODEL_AVAILABLE = False
    _GLOBAL_LOG_PRIOR = None
    _EVAL_LOG_PRIORS = {}
    _COND_LOG_PROBS = None

    if pd is None:
        _IS_INITIALIZED = True
        return

    data_path = _find_data_path()

    try:
        corr_cols = [_TIER_TO_MODEL[t] for t in _CLASS_LABELS]
        cost_cols = [m + "|total_cost" for m in corr_cols]
        usecols = ["prompt", "eval_name"] + corr_cols + cost_cols

        df = pd.read_csv(data_path, usecols=usecols)

        corr_mat = df[corr_cols].to_numpy(dtype=float)
        cost_mat = df[cost_cols].to_numpy(dtype=float)

        mask = np.isfinite(corr_mat).all(axis=1) & np.isfinite(cost_mat).all(axis=1)
        mask &= df["prompt"].notna().to_numpy()
        mask &= df["eval_name"].notna().to_numpy()

        if not mask.any():
            _IS_INITIALIZED = True
            return

        df_valid = df[mask].reset_index(drop=True)
        corr_valid = corr_mat[mask]
        cost_valid = cost_mat[mask]

        scores = corr_valid - _LAMBDA_COST * cost_valid
        labels_idx = scores.argmax(axis=1)  # shape: (n_samples,)

        n_samples = df_valid.shape[0]
        C = _NUM_CLASSES
        V = _VOCAB_SIZE

        class_doc_count = np.zeros(C, dtype=np.int64)
        total_token_counts = np.zeros(C, dtype=np.int64)
        class_token_counts = np.zeros((C, V), dtype=np.int64)

        eval_class_counts = {}  # eval_key -> np.array(C,)

        prompts = df_valid["prompt"].tolist()
        eval_names = df_valid["eval_name"].tolist()

        for i in range(n_samples):
            c = int(labels_idx[i])
            class_doc_count[c] += 1

            e_raw = eval_names[i]
            e_key = str(e_raw).strip().lower()
            arr = eval_class_counts.get(e_key)
            if arr is None:
                arr = np.zeros(C, dtype=np.int64)
                eval_class_counts[e_key] = arr
            arr[c] += 1

            text = prompts[i]
            tokens = _tokenize(text)
            if not tokens:
                continue
            total_token_counts[c] += len(tokens)
            for tok in tokens:
                idx = hash(tok) % V
                class_token_counts[c, idx] += 1

        if class_doc_count.sum() == 0:
            _IS_INITIALIZED = True
            return

        priors = (class_doc_count.astype(np.float64) + _ALPHA_PRIOR) / (
            float(n_samples) + _ALPHA_PRIOR * C
        )
        _GLOBAL_LOG_PRIOR = np.log(priors).astype(np.float32)

        cond_log = np.empty((C, V), dtype=np.float32)
        for c in range(C):
            denom = float(total_token_counts[c]) + _ALPHA * V
            probs_c = (class_token_counts[c].astype(np.float64) + _ALPHA) / denom
            cond_log[c] = np.log(probs_c).astype(np.float32)
        _COND_LOG_PROBS = cond_log

        eval_log_priors = {}
        for e_key, counts in eval_class_counts.items():
            total = counts.sum()
            if total <= 0:
                continue
            pri_e = (counts.astype(np.float64) + _ALPHA_PRIOR) / (
                float(total) + _ALPHA_PRIOR * C
            )
            eval_log_priors[e_key] = np.log(pri_e).astype(np.float32)
        _EVAL_LOG_PRIORS = eval_log_priors

        _MODEL_AVAILABLE = True

    except Exception:
        _MODEL_AVAILABLE = False
    finally:
        _IS_INITIALIZED = True
        try:
            del df  # type: ignore[name-defined]
        except Exception:
            pass


def _predict_tier(query: str, eval_name: str) -> str:
    if not _MODEL_AVAILABLE or _COND_LOG_PROBS is None or _GLOBAL_LOG_PRIOR is None:
        return "cheap"

    tokens = _tokenize(query)
    scores = _GLOBAL_LOG_PRIOR.copy()

    if eval_name is not None:
        eval_key = str(eval_name).strip().lower()
        pri = _EVAL_LOG_PRIORS.get(eval_key)
        if pri is not None:
            scores = pri.copy()

    if tokens:
        cond = _COND_LOG_PROBS
        for tok in tokens:
            idx = hash(tok) % _VOCAB_SIZE
            scores += cond[:, idx]

    pred_idx = int(scores.argmax())
    return _INDEX_TO_LABEL.get(pred_idx, "cheap")


class Solution:
    def __init__(self):
        _initialize_model()

    def solve(self, query: str, eval_name: str, candidate_models: List[str]) -> str:
        _initialize_model()

        if not candidate_models:
            candidate_models = ["cheap", "mid", "expensive"]

        if _MODEL_AVAILABLE:
            pred_label = _predict_tier(query, eval_name)
        else:
            pred_label = "cheap"

        if pred_label in candidate_models:
            return pred_label

        rank_map = {"cheap": 0, "mid": 1, "expensive": 2}

        if pred_label not in rank_map:
            return candidate_models[0]

        pred_rank = rank_map[pred_label]
        best_cand = None
        best_key = None

        for cand in candidate_models:
            r = rank_map.get(cand)
            if r is None:
                continue
            dist = abs(r - pred_rank)
            key = (dist, r)
            if best_key is None or key < best_key:
                best_key = key
                best_cand = cand

        if best_cand is not None:
            return best_cand

        return candidate_models[0]