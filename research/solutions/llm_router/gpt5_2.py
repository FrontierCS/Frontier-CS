import os
import re
import math
from typing import Dict, List
import pandas as pd
import numpy as np


class _RouterState:
    initialized = False
    tier_to_model: Dict[str, str] = {
        "cheap": "mistralai/mistral-7b-chat",
        "mid": "mistralai/mixtral-8x7b-chat",
        "expensive": "gpt-4-1106-preview",
    }
    model_cols: Dict[str, str] = {}
    cost_cols: Dict[str, str] = {}
    lambda_cost = 150.0
    df: pd.DataFrame = None
    available_tiers: List[str] = ["cheap", "mid", "expensive"]

    # Costs and accuracies
    avg_cost_by_tier: Dict[str, float] = {}
    global_acc_by_tier: Dict[str, float] = {}

    # Grouped stats
    acc_by_eval: Dict[str, Dict[str, float]] = {}
    acc_by_lenbin: Dict[int, Dict[str, float]] = {}
    acc_by_flag_mc: Dict[bool, Dict[str, float]] = {}
    acc_by_flag_code: Dict[bool, Dict[str, float]] = {}
    acc_by_flag_math: Dict[bool, Dict[str, float]] = {}

    count_by_eval: Dict[str, int] = {}
    count_by_lenbin: Dict[int, int] = {}
    count_by_flag_mc: Dict[bool, int] = {}
    count_by_flag_code: Dict[bool, int] = {}
    count_by_flag_math: Dict[bool, int] = {}

    # Smoothing hyperparameters and weights
    alpha = 50.0
    weights = {
        "global": 0.3,
        "eval": 3.5,
        "length": 0.9,
        "mc": 0.9,
        "code": 1.3,
        "math": 1.2,
    }

    # Compiled regex patterns
    re_mc = re.compile(r"(^|\n)\s*[A-E][\)\.]\s", re.IGNORECASE)
    re_code = re.compile(r"```|(^|\n)\s*(def |class |#include|import )|Write a function", re.IGNORECASE)
    re_math_keywords = re.compile(
        r"\b(solve|equation|sum|product|probability|median|mean|mode|integral|derivative|limit|geometry|algebra|"
        r"triangle|circle|angle|perimeter|area|gcd|lcm|modulo|remainder|fraction|polynomial|prime|factor|matrix|vector|"
        r"eigenvalue|determinant|log|ln|power|square root|cube root|simplify)\b",
        re.IGNORECASE,
    )

    @classmethod
    def _safe_read_reference(cls) -> pd.DataFrame:
        paths = [
            "resources/reference_data.csv",
            os.path.join(os.getcwd(), "resources", "reference_data.csv"),
        ]
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            paths.append(os.path.join(base_dir, "resources", "reference_data.csv"))
            # In some setups the solution sits in solutions/, so go one level up
            paths.append(os.path.join(os.path.dirname(base_dir), "resources", "reference_data.csv"))
        except Exception:
            pass

        for p in paths:
            if os.path.exists(p):
                try:
                    return pd.read_csv(p)
                except Exception:
                    continue
        return None

    @classmethod
    def _len_bin(cls, text: str) -> int:
        n = len(text or "")
        if n < 180:
            return 0
        if n < 400:
            return 1
        if n < 1200:
            return 2
        return 3

    @classmethod
    def _has_mc(cls, text: str) -> bool:
        if not text:
            return False
        if cls.re_mc.search(text):
            return True
        # Additional heuristic: presence of choices labeled A) ... D)
        choices = 0
        for ch in ["A)", "B)", "C)", "D)"]:
            if ch in text:
                choices += 1
        if choices >= 3:
            return True
        if "Answer choices" in text or "Answer Choices" in text or "Options:" in text:
            return True
        return False

    @classmethod
    def _has_code(cls, text: str) -> bool:
        if not text:
            return False
        if cls.re_code.search(text):
            return True
        # Heuristic for code-like prompts in MBPP-style text without code fences
        code_keywords = ["function", "python", "list", "string", "array", "dictionary", "regex", "SQL"]
        matches = sum(1 for kw in code_keywords if kw.lower() in text.lower())
        return matches >= 2

    @classmethod
    def _has_math(cls, text: str) -> bool:
        if not text:
            return False
        if cls.re_math_keywords.search(text):
            return True
        # Digit density heuristic
        digits = sum(c.isdigit() for c in text)
        if len(text) > 0 and (digits / len(text)) >= 0.08:
            return True
        return False

    @classmethod
    def _extract_flags(cls, text: str):
        return {
            "lenbin": cls._len_bin(text),
            "mc": cls._has_mc(text),
            "code": cls._has_code(text),
            "math": cls._has_math(text),
        }

    @classmethod
    def _safemean(cls, series: pd.Series) -> float:
        try:
            return float(np.nanmean(series))
        except Exception:
            try:
                return float(series.mean())
            except Exception:
                return 0.0

    @classmethod
    def _dirichlet_smooth(cls, correct_sum: float, total: int, global_p: float) -> float:
        # (sum_correct + alpha * p_global) / (n + alpha)
        if total is None or total <= 0:
            return float(global_p)
        numerator = correct_sum + cls.alpha * global_p
        denominator = total + cls.alpha
        p = numerator / denominator if denominator > 0 else global_p
        # clamp to [0,1]
        p = max(0.0, min(1.0, p))
        return p

    @classmethod
    def _compute_group_stats(cls):
        df = cls.df
        tier_models = cls.tier_to_model

        # Map cols
        cls.model_cols = {tier: tier_models[tier] for tier in tier_models}
        cls.cost_cols = {tier: f"{tier_models[tier]}|total_cost" for tier in tier_models}

        # Filter only those rows where correctness is available for our three models
        required_cols = [cls.model_cols[t] for t in cls.available_tiers if cls.model_cols.get(t) in df.columns]
        # If any is missing, just proceed with available columns
        available_tiers = [t for t in cls.available_tiers if cls.model_cols.get(t) in df.columns]
        if not available_tiers:
            # No matching columns; set safe defaults
            cls.global_acc_by_tier = {t: 0.0 for t in cls.available_tiers}
            cls.avg_cost_by_tier = {t: 0.0 for t in cls.available_tiers}
            return
        cls.available_tiers = available_tiers

        # Compute avg cost per tier
        for t in cls.available_tiers:
            cost_col = cls.cost_cols.get(t)
            if cost_col in df.columns:
                cls.avg_cost_by_tier[t] = cls._safemean(df[cost_col])
            else:
                # Fallback: typical costs if missing
                if t == "cheap":
                    cls.avg_cost_by_tier[t] = 1.8e-05
                elif t == "mid":
                    cls.avg_cost_by_tier[t] = 7.0e-05
                else:
                    cls.avg_cost_by_tier[t] = 8.8e-04

        # Global accuracies
        for t in cls.available_tiers:
            acc_col = cls.model_cols[t]
            cls.global_acc_by_tier[t] = cls._safemean(df[acc_col].astype(float))

        # Prepare features for grouping
        texts = df["prompt"].astype(str).fillna("")
        lenbins = [cls._len_bin(x) for x in texts]
        mcs = [cls._has_mc(x) for x in texts]
        codes = [cls._has_code(x) for x in texts]
        maths = [cls._has_math(x) for x in texts]
        df = df.copy()
        df["_lenbin"] = lenbins
        df["_mc"] = mcs
        df["_code"] = codes
        df["_math"] = maths
        cls.df = df

        # Group by eval_name
        cls.acc_by_eval = {}
        cls.count_by_eval = {}
        for ev, g in df.groupby("eval_name"):
            cls.count_by_eval[ev] = int(len(g))
            p_by_tier = {}
            for t in cls.available_tiers:
                acc_col = cls.model_cols[t]
                p = cls._safemean(g[acc_col].astype(float))
                # Smooth towards global
                p_sm = cls._dirichlet_smooth(p * len(g), len(g), cls.global_acc_by_tier[t])
                p_by_tier[t] = p_sm
            cls.acc_by_eval[ev] = p_by_tier

        # Group by length bin
        cls.acc_by_lenbin = {}
        cls.count_by_lenbin = {}
        for lb, g in df.groupby("_lenbin"):
            cls.count_by_lenbin[int(lb)] = int(len(g))
            p_by_tier = {}
            for t in cls.available_tiers:
                acc_col = cls.model_cols[t]
                p = cls._safemean(g[acc_col].astype(float))
                p_sm = cls._dirichlet_smooth(p * len(g), len(g), cls.global_acc_by_tier[t])
                p_by_tier[t] = p_sm
            cls.acc_by_lenbin[int(lb)] = p_by_tier

        # Group by MC flag
        cls.acc_by_flag_mc = {}
        cls.count_by_flag_mc = {}
        for val, g in df.groupby("_mc"):
            cls.count_by_flag_mc[bool(val)] = int(len(g))
            p_by_tier = {}
            for t in cls.available_tiers:
                acc_col = cls.model_cols[t]
                p = cls._safemean(g[acc_col].astype(float))
                p_sm = cls._dirichlet_smooth(p * len(g), len(g), cls.global_acc_by_tier[t])
                p_by_tier[t] = p_sm
            cls.acc_by_flag_mc[bool(val)] = p_by_tier

        # Group by code flag
        cls.acc_by_flag_code = {}
        cls.count_by_flag_code = {}
        for val, g in df.groupby("_code"):
            cls.count_by_flag_code[bool(val)] = int(len(g))
            p_by_tier = {}
            for t in cls.available_tiers:
                acc_col = cls.model_cols[t]
                p = cls._safemean(g[acc_col].astype(float))
                p_sm = cls._dirichlet_smooth(p * len(g), len(g), cls.global_acc_by_tier[t])
                p_by_tier[t] = p_sm
            cls.acc_by_flag_code[bool(val)] = p_by_tier

        # Group by math flag
        cls.acc_by_flag_math = {}
        cls.count_by_flag_math = {}
        for val, g in df.groupby("_math"):
            cls.count_by_flag_math[bool(val)] = int(len(g))
            p_by_tier = {}
            for t in cls.available_tiers:
                acc_col = cls.model_cols[t]
                p = cls._safemean(g[acc_col].astype(float))
                p_sm = cls._dirichlet_smooth(p * len(g), len(g), cls.global_acc_by_tier[t])
                p_by_tier[t] = p_sm
            cls.acc_by_flag_math[bool(val)] = p_by_tier

    @classmethod
    def initialize(cls):
        if cls.initialized:
            return
        df = cls._safe_read_reference()
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            # Create minimal defaults if dataset is missing
            cls.df = pd.DataFrame()
            cls.avg_cost_by_tier = {"cheap": 1.8e-05, "mid": 7.0e-05, "expensive": 8.8e-04}
            cls.global_acc_by_tier = {"cheap": 0.5, "mid": 0.6, "expensive": 0.75}
            cls.acc_by_eval = {}
            cls.acc_by_lenbin = {}
            cls.acc_by_flag_mc = {}
            cls.acc_by_flag_code = {}
            cls.acc_by_flag_math = {}
            cls.count_by_eval = {}
            cls.count_by_lenbin = {}
            cls.count_by_flag_mc = {}
            cls.count_by_flag_code = {}
            cls.count_by_flag_math = {}
            cls.initialized = True
            return

        # Ensure required columns exist
        needed_cols = set(["prompt", "eval_name"])
        for name in cls.tier_to_model.values():
            needed_cols.add(name)
            needed_cols.add(f"{name}|total_cost")
        missing = [c for c in needed_cols if c not in df.columns]
        # If some columns are missing, continue with those available and handle gracefully
        cls.df = df
        cls._compute_group_stats()
        cls.initialized = True

    @classmethod
    def _weighted_probability(cls, eval_name: str, flags: Dict):
        # Gather probabilities from groups with weights based on group support
        # Always include global
        contributions = []
        weights = []

        # Global base
        for t in cls.available_tiers:
            p = cls.global_acc_by_tier.get(t, 0.0)
            contributions.append((t, p, "global"))
        weights.append(("global", cls.weights["global"], len(cls.df) if cls.df is not None else 1000))

        # Eval_name specific
        if eval_name in cls.acc_by_eval:
            p_by_tier = cls.acc_by_eval[eval_name]
            n = cls.count_by_eval.get(eval_name, 0)
            if n <= 0:
                n = 1
            for t in cls.available_tiers:
                contributions.append((t, p_by_tier.get(t, cls.global_acc_by_tier.get(t, 0.0)), "eval"))
            weights.append(("eval", cls.weights["eval"], n))

        # Length bin
        lb = flags.get("lenbin", 1)
        if lb in cls.acc_by_lenbin:
            p_by_tier = cls.acc_by_lenbin[lb]
            n = cls.count_by_lenbin.get(lb, 0)
            if n <= 0:
                n = 1
            for t in cls.available_tiers:
                contributions.append((t, p_by_tier.get(t, cls.global_acc_by_tier.get(t, 0.0)), "length"))
            weights.append(("length", cls.weights["length"], n))

        # Multiple choice
        mc = bool(flags.get("mc", False))
        if mc in cls.acc_by_flag_mc:
            p_by_tier = cls.acc_by_flag_mc[mc]
            n = cls.count_by_flag_mc.get(mc, 0)
            if n <= 0:
                n = 1
            for t in cls.available_tiers:
                contributions.append((t, p_by_tier.get(t, cls.global_acc_by_tier.get(t, 0.0)), "mc"))
            weights.append(("mc", cls.weights["mc"], n))

        # Code
        code = bool(flags.get("code", False))
        if code in cls.acc_by_flag_code:
            p_by_tier = cls.acc_by_flag_code[code]
            n = cls.count_by_flag_code.get(code, 0)
            if n <= 0:
                n = 1
            for t in cls.available_tiers:
                contributions.append((t, p_by_tier.get(t, cls.global_acc_by_tier.get(t, 0.0)), "code"))
            weights.append(("code", cls.weights["code"], n))

        # Math
        math_flag = bool(flags.get("math", False))
        if math_flag in cls.acc_by_flag_math:
            p_by_tier = cls.acc_by_flag_math[math_flag]
            n = cls.count_by_flag_math.get(math_flag, 0)
            if n <= 0:
                n = 1
            for t in cls.available_tiers:
                contributions.append((t, p_by_tier.get(t, cls.global_acc_by_tier.get(t, 0.0)), "math"))
            weights.append(("math", cls.weights["math"], n))

        # Aggregate weighted probabilities per tier
        # Compute effective weight per source with confidence from sample size
        weight_by_source = {}
        for src, base_w, n in weights:
            # Confidence scaling: sqrt(min(n, cap)/cap)
            cap = 300.0
            conf = math.sqrt(min(float(n), cap) / cap)
            weight_by_source[src] = base_w * conf

        sum_weights = {t: 0.0 for t in cls.available_tiers}
        sum_weighted_p = {t: 0.0 for t in cls.available_tiers}

        for t, p, src in contributions:
            w = weight_by_source.get(src, 0.0)
            sum_weights[t] += w
            sum_weighted_p[t] += w * p

        p_final = {}
        for t in cls.available_tiers:
            if sum_weights[t] > 0:
                p_final[t] = sum_weighted_p[t] / sum_weights[t]
            else:
                p_final[t] = cls.global_acc_by_tier.get(t, 0.0)
            # Final clamp
            p_final[t] = max(0.0, min(1.0, float(p_final[t])))
        return p_final

    @classmethod
    def route(cls, query: str, eval_name: str, candidate_models: List[str]) -> str:
        cls.initialize()

        # Filter candidates to known tiers
        candidates = [c for c in candidate_models if c in cls.available_tiers]
        if not candidates:
            # Fallback: return the first candidate if unknown
            return candidate_models[0] if candidate_models else "cheap"

        flags = cls._extract_flags(query or "")
        p_by_tier = cls._weighted_probability(eval_name, flags)

        # Compute expected score for each candidate: p - lambda * cost
        best_tier = candidates[0]
        best_score = -1e9
        for t in candidates:
            p = p_by_tier.get(t, cls.global_acc_by_tier.get(t, 0.0))
            cost = cls.avg_cost_by_tier.get(t, 0.0)
            score = float(p) - cls.lambda_cost * float(cost)
            # Additional tie-breaking: prefer cheaper when equal within small epsilon
            if score > best_score + 1e-6:
                best_score = score
                best_tier = t
            elif abs(score - best_score) <= 1e-6:
                # tie-break by lower cost
                if cls.avg_cost_by_tier.get(t, 1.0) < cls.avg_cost_by_tier.get(best_tier, 1.0):
                    best_tier = t
                    best_score = score

        # Simple risk-averse adjustment:
        # If predicted p for cheap is very close to mid, prefer cheap due to cost unless mid gains > delta_threshold
        if "cheap" in candidates and "mid" in candidates:
            p_c = p_by_tier.get("cheap", 0.0)
            p_m = p_by_tier.get("mid", 0.0)
            delta_cost = cls.lambda_cost * (cls.avg_cost_by_tier.get("mid", 0.0) - cls.avg_cost_by_tier.get("cheap", 0.0))
            # Choose mid only if expected gain significantly exceeds cost by margin
            if best_tier == "mid" and (p_m - p_c) < (delta_cost + 0.01):
                best_tier = "cheap"
        # Similar adjustment for expensive vs mid
        if "mid" in candidates and "expensive" in candidates:
            p_m = p_by_tier.get("mid", 0.0)
            p_e = p_by_tier.get("expensive", 0.0)
            delta_cost = cls.lambda_cost * (cls.avg_cost_by_tier.get("expensive", 0.0) - cls.avg_cost_by_tier.get("mid", 0.0))
            if best_tier == "expensive" and (p_e - p_m) < (delta_cost + 0.02):
                best_tier = "mid"

        # For explicitly "easy" MC with short length, bias towards cheap if not strongly in favor of others
        if flags.get("mc") and flags.get("lenbin", 2) <= 1 and "cheap" in candidates:
            if best_tier != "cheap":
                # If cheap score within margin
                cheap_score = p_by_tier.get("cheap", 0.0) - cls.lambda_cost * cls.avg_cost_by_tier.get("cheap", 0.0)
                best_score_val = p_by_tier.get(best_tier, 0.0) - cls.lambda_cost * cls.avg_cost_by_tier.get(best_tier, 0.0)
                if (best_score_val - cheap_score) < 0.015:
                    best_tier = "cheap"

        return best_tier


class Solution:
    def solve(self, query: str, eval_name: str, candidate_models: List[str]) -> str:
        try:
            return _RouterState.route(query, eval_name, candidate_models)
        except Exception:
            # Fail-safe: try to return a valid candidate to avoid zero
            for tier in ["cheap", "mid", "expensive"]:
                if tier in candidate_models:
                    return tier
            return candidate_models[0] if candidate_models else "cheap"