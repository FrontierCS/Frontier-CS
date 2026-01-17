import os
import csv
import math
import re


class NaiveBayesRouter:
    def __init__(self):
        self.tiers = ["cheap", "mid", "expensive"]
        self.tier_to_model = {
            "cheap": "mistralai/mistral-7b-chat",
            "mid": "mistralai/mixtral-8x7b-chat",
            "expensive": "gpt-4-1106-preview",
        }
        self.lambda_cost = 150.0
        self.alpha_prior = 1.0
        self.alpha_word = 1.0
        self.max_tokens_per_doc = 256
        self._token_pattern = re.compile(r"[a-z0-9_]+")
        self.trained = False
        self.label_priors = {}
        self.label_denoms = {}
        self.token_counts_by_label = {}
        self.label_total_tokens = {}
        self.label_counts = {}
        self.vocab_size = 0
        self.per_eval_best = {}
        self.global_best = "cheap"
        data_path = self._locate_data_file()
        if data_path is not None:
            try:
                self._train_from_file(data_path)
            except Exception:
                self.trained = False

    def _locate_data_file(self):
        candidates = []
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            candidates.append(os.path.join(base_dir, "resources", "reference_data.csv"))
        except Exception:
            pass
        cwd = os.getcwd()
        candidates.append(os.path.join(cwd, "resources", "reference_data.csv"))
        candidates.append("resources/reference_data.csv")
        seen = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            if os.path.exists(path):
                return path
        return None

    def _safe_float(self, x):
        try:
            if x is None:
                return 0.0
            if isinstance(x, (int, float)):
                val = float(x)
            else:
                s = str(x).strip()
                if not s:
                    return 0.0
                val = float(s)
            if not math.isfinite(val):
                return 0.0
            return val
        except Exception:
            return 0.0

    def _tokenize(self, prompt, eval_name):
        if not isinstance(prompt, str):
            prompt = "" if prompt is None else str(prompt)
        text = prompt.lower()
        tokens = self._token_pattern.findall(text)
        if len(tokens) > self.max_tokens_per_doc:
            tokens = tokens[:self.max_tokens_per_doc]
        if eval_name is not None:
            if not isinstance(eval_name, str):
                eval_name = str(eval_name)
            eval_name = eval_name.strip().lower()
            if eval_name:
                tokens.append("__eval__" + eval_name)
        return tokens

    def _train_from_file(self, path):
        label_counts = {tier: 0 for tier in self.tiers}
        label_total_tokens = {tier: 0 for tier in self.tiers}
        token_counts_by_label = {tier: {} for tier in self.tiers}
        vocab = set()
        per_eval_reward_sums = {}
        global_reward_sums = {tier: 0.0 for tier in self.tiers}
        total_docs = 0
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                self.trained = False
                return
            fieldnames = set(reader.fieldnames)
            for tier in self.tiers:
                model = self.tier_to_model.get(tier)
                if model is None:
                    self.trained = False
                    return
                if model not in fieldnames or (model + "|total_cost") not in fieldnames:
                    self.trained = False
                    return
            for row in reader:
                total_docs += 1
                eval_name = row.get("eval_name", "")
                if eval_name is None:
                    eval_name = ""
                eval_name = str(eval_name)
                scores = {}
                costs = {}
                for tier in self.tiers:
                    model = self.tier_to_model[tier]
                    acc = self._safe_float(row.get(model, ""))
                    cost = self._safe_float(row.get(model + "|total_cost", ""))
                    score = acc - self.lambda_cost * cost
                    scores[tier] = score
                    costs[tier] = cost
                best_tier = None
                best_score = None
                for tier in self.tiers:
                    s = scores[tier]
                    if best_tier is None or s > best_score:
                        best_tier = tier
                        best_score = s
                    elif s == best_score and costs[tier] < costs[best_tier]:
                        best_tier = tier
                        best_score = s
                label_counts[best_tier] += 1
                prompt = row.get("prompt", "")
                tokens = self._tokenize(prompt, eval_name)
                n_tokens = len(tokens)
                if n_tokens:
                    label_total_tokens[best_tier] += n_tokens
                    counts_for_label = token_counts_by_label[best_tier]
                    for tok in tokens:
                        counts_for_label[tok] = counts_for_label.get(tok, 0) + 1
                        if tok not in vocab:
                            vocab.add(tok)
                if eval_name not in per_eval_reward_sums:
                    per_eval_reward_sums[eval_name] = {tier: 0.0 for tier in self.tiers}
                for tier in self.tiers:
                    r = scores[tier]
                    per_eval_reward_sums[eval_name][tier] += r
                    global_reward_sums[tier] += r
        if total_docs == 0 or not vocab:
            self.trained = False
            return
        self.vocab_size = len(vocab)
        self.label_counts = label_counts
        self.label_total_tokens = label_total_tokens
        self.token_counts_by_label = token_counts_by_label
        denom_docs = total_docs + self.alpha_prior * len(self.tiers)
        label_priors = {}
        for tier in self.tiers:
            label_priors[tier] = (label_counts[tier] + self.alpha_prior) / denom_docs
        self.label_priors = label_priors
        label_denoms = {}
        for tier in self.tiers:
            denom = label_total_tokens[tier] + self.alpha_word * self.vocab_size
            if denom <= 0.0:
                denom = self.alpha_word * self.vocab_size
            label_denoms[tier] = denom
        self.label_denoms = label_denoms
        per_eval_best = {}
        for eval_name, sums in per_eval_reward_sums.items():
            best_tier = None
            best_val = None
            for tier in self.tiers:
                v = sums.get(tier, float("-inf"))
                if best_tier is None or v > best_val:
                    best_tier = tier
                    best_val = v
            per_eval_best[eval_name] = best_tier
        self.per_eval_best = per_eval_best
        best_global = None
        best_val = None
        for tier in self.tiers:
            v = global_reward_sums.get(tier, float("-inf"))
            if best_global is None or v > best_val:
                best_global = tier
                best_val = v
        if best_global is None:
            best_global = "cheap"
        self.global_best = best_global
        self.trained = True

    def _fallback_by_eval(self, eval_name, available_labels):
        if eval_name is not None:
            if not isinstance(eval_name, str):
                eval_name = str(eval_name)
            eval_name = eval_name.strip()
            if eval_name and self.per_eval_best:
                t = self.per_eval_best.get(eval_name)
                if t in available_labels:
                    return t
        if self.global_best in available_labels:
            return self.global_best
        if self.trained and self.label_priors:
            best = None
            best_prior = None
            for t in available_labels:
                p = self.label_priors.get(t, 0.0)
                if best is None or p > best_prior:
                    best = t
                    best_prior = p
            if best is not None:
                return best
        return available_labels[0]

    def route(self, query, eval_name, candidate_models):
        if not candidate_models:
            return "cheap"
        available_labels = [tier for tier in self.tiers if tier in candidate_models]
        if not available_labels:
            return candidate_models[0]
        if not self.trained or self.vocab_size <= 0:
            return self._fallback_by_eval(eval_name, available_labels)
        tokens = self._tokenize(query, eval_name)
        if not tokens:
            return self._fallback_by_eval(eval_name, available_labels)
        label_scores = {}
        for tier in available_labels:
            prior = self.label_priors.get(tier)
            if prior is None or prior <= 0.0:
                continue
            score = math.log(prior)
            denom = self.label_denoms.get(tier)
            if not denom or denom <= 0.0:
                denom = self.alpha_word * max(self.vocab_size, 1)
            counts_for_label = self.token_counts_by_label.get(tier, {})
            for tok in tokens:
                c = counts_for_label.get(tok, 0)
                score += math.log((c + self.alpha_word) / denom)
            label_scores[tier] = score
        if not label_scores:
            return self._fallback_by_eval(eval_name, available_labels)
        best_tier = None
        best_score = None
        for tier, s in label_scores.items():
            if best_tier is None or s > best_score:
                best_tier = tier
                best_score = s
        if best_tier is None:
            return self._fallback_by_eval(eval_name, available_labels)
        return best_tier


_GLOBAL_ROUTER = None


class Solution:
    def __init__(self):
        global _GLOBAL_ROUTER
        if _GLOBAL_ROUTER is None:
            _GLOBAL_ROUTER = NaiveBayesRouter()
        self._router = _GLOBAL_ROUTER

    def solve(self, query, eval_name, candidate_models):
        try:
            return self._router.route(query, eval_name, candidate_models)
        except Exception:
            if candidate_models:
                return candidate_models[0]
            return "cheap"