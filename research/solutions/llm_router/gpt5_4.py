import os
import re
import math
import pandas as pd
from collections import Counter, defaultdict

LAMBDA_COST = 150.0

def _find_data_path():
    # Try multiple approaches to locate the CSV
    candidates = [
        "resources/reference_data.csv",
        os.path.join(os.getcwd(), "resources", "reference_data.csv"),
    ]
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(here, "resources", "reference_data.csv"))
        candidates.append(os.path.join(os.path.dirname(here), "resources", "reference_data.csv"))
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(here)), "resources", "reference_data.csv"))
    except Exception:
        pass
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None

def _safe_lower(s):
    try:
        return s.lower()
    except Exception:
        try:
            return str(s).lower()
        except Exception:
            return ""

class TextFeaturizer:
    def __init__(self):
        # Precompile regex
        self._token_re = re.compile(r"[a-z0-9]+")
        self._multi_choice_re = re.compile(r"(^|\n)\s*[A-H]\)")
        self._letter_option_re = re.compile(r"\b[A-H]\)")
        self._roman_option_re = re.compile(r"\b(i{1,3}|iv|v|vi{0,3}|ix|x)\)")
        self._true_false_re = re.compile(r"true|false", re.IGNORECASE)
        self._code_markers = [
            "def ", "class ", "return ", "import ", "from ", "print(", "```", "/*", "//", "#include", "public static", "System.out", "->", "lambda ", "function "
        ]
        self._math_markers = [
            "solve", "probability", "integral", "derivative", "equation", "inequality",
            "algebra", "geometry", "triangle", "prime", "factor", "multiple", "sum",
            "product", "ratio", "percent", "percentage", "average", "mean", "median",
            "variance", "gcd", "lcm", "mod", "remainder"
        ]
        self._sql_markers = ["select ", "join ", "where ", "group by", "order by", "insert into", "update ", "delete "]

    def basic_tokenize(self, text):
        text = _safe_lower(text)
        # Normalize digits to '0'
        text = re.sub(r"\d", "0", text)
        tokens = self._token_re.findall(text)
        return tokens

    def tokenize(self, text, eval_name=None):
        t = _safe_lower(text)
        orig = t
        # Normalize digits to '0'
        t = re.sub(r"\d", "0", t)
        tokens = self._token_re.findall(t)

        # Special features
        extras = []

        # Multi-choice detection
        if self._multi_choice_re.search(orig) or self._letter_option_re.search(orig) or self._roman_option_re.search(orig):
            extras.append("FEAT_MCQ")

        # True/False detection
        if self._true_false_re.search(orig):
            extras.append("FEAT_TRUEFALSE")

        # Code markers
        if any(marker in orig for marker in self._code_markers):
            extras.append("TOPIC_CODE")

        # SQL markers
        if any(marker in orig for marker in self._sql_markers):
            extras.append("TOPIC_SQL")

        # Math markers
        if any(m in orig for m in self._math_markers):
            extras.append("TOPIC_MATH")

        # Has numbers
        if re.search(r"\d", orig):
            extras.append("HAS_NUM")

        # Newlines
        nlines = orig.count("\n")
        if nlines > 0:
            extras.append("HAS_NL")
        if nlines > 3:
            extras.append("MANY_NL")

        # Length buckets
        n_tokens = len(tokens)
        if n_tokens <= 10:
            extras.append("LEN_0_10")
        elif n_tokens <= 25:
            extras.append("LEN_11_25")
        elif n_tokens <= 50:
            extras.append("LEN_26_50")
        elif n_tokens <= 100:
            extras.append("LEN_51_100")
        elif n_tokens <= 200:
            extras.append("LEN_101_200")
        else:
            extras.append("LEN_200_PLUS")

        # Eval_name feature
        if eval_name:
            en = _safe_lower(eval_name)
            extras.append("TASK_" + en)
            # Split by separators to get subject
            parts = re.split(r"[._\-:/]+", en)
            for p in parts:
                if len(p) > 0:
                    extras.append("TASKPART_" + p)

        return tokens + extras

class MultinomialNB:
    def __init__(self, alpha=1.0):
        self.alpha = alpha
        self.word_counts = defaultdict(lambda: [0.0, 0.0])  # token -> [count_in_class0, count_in_class1]
        self.class_token_counts = [0.0, 0.0]  # total token counts per class
        self.class_doc_counts = [0.0, 0.0]    # number of docs per class
        self.vocab_size = 0
        self.fitted = False

    def fit(self, docs, labels):
        # docs: list of list tokens
        # labels: 0 or 1
        for doc, y in zip(docs, labels):
            y01 = 1 if y == 1 or y is True else 0
            self.class_doc_counts[y01] += 1.0
            cnt = Counter(doc)
            # Use token frequency as in standard multinomial NB
            for token, c in cnt.items():
                self.word_counts[token][y01] += float(c)
                self.class_token_counts[y01] += float(c)
        self.vocab_size = len(self.word_counts)
        self.fitted = True

    def predict_log_proba(self, doc):
        if not self.fitted or self.vocab_size == 0:
            # If not fitted, return equal probabilities
            return [math.log(0.5), math.log(0.5)]
        total_docs = self.class_doc_counts[0] + self.class_doc_counts[1]
        # To avoid zero prior
        prior0 = (self.class_doc_counts[0] + 1.0) / (total_docs + 2.0)
        prior1 = (self.class_doc_counts[1] + 1.0) / (total_docs + 2.0)
        logp0 = math.log(prior0)
        logp1 = math.log(prior1)
        # Denominator terms for likelihood
        denom0 = self.class_token_counts[0] + self.alpha * self.vocab_size
        denom1 = self.class_token_counts[1] + self.alpha * self.vocab_size

        cnt = Counter(doc)
        # Accumulate log likelihoods
        for token, c in cnt.items():
            wc0, wc1 = self.word_counts.get(token, (0.0, 0.0))
            # Laplace smoothing
            p_t_c0 = (wc0 + self.alpha) / denom0
            p_t_c1 = (wc1 + self.alpha) / denom1
            # Guard against underflow
            if p_t_c0 <= 0.0:
                p_t_c0 = 1e-12
            if p_t_c1 <= 0.0:
                p_t_c1 = 1e-12
            logp0 += float(c) * math.log(p_t_c0)
            logp1 += float(c) * math.log(p_t_c1)
        return [logp0, logp1]

    def predict_proba_correct(self, doc):
        logp0, logp1 = self.predict_log_proba(doc)
        m = max(logp0, logp1)
        e0 = math.exp(logp0 - m)
        e1 = math.exp(logp1 - m)
        s = e0 + e1
        if s <= 0.0:
            return 0.5
        return e1 / s

class RouterModel:
    def __init__(self):
        self.featurizer = TextFeaturizer()

        # Mapping from routing tiers to columns used in training
        self.tier_to_model_col = {
            "cheap": "mistralai/mistral-7b-chat",
            "mid": "mistralai/mixtral-8x7b-chat",
            "expensive": "gpt-4-1106-preview",
        }
        self.tiers = ["cheap", "mid", "expensive"]

        self.global_models = {}  # tier -> MultinomialNB
        self.dataset_models = defaultdict(dict)  # eval_name -> { tier -> MultinomialNB }
        self.dataset_model_counts = defaultdict(lambda: defaultdict(int))  # eval_name -> { tier -> n_samples }
        self.dataset_default_route = {}  # eval_name -> default best tier by utility
        self.global_default_route = "cheap"

        self.cost_median = {}  # tier -> median cost
        self.cost_regression = {}  # tier -> (a, b)

        self.global_prior_correct = {}  # tier -> base rate
        self.dataset_prior_correct = defaultdict(dict)  # eval_name -> { tier -> base rate }

        # Train using available reference data
        self._train_from_reference()

    def _train_from_reference(self):
        path = _find_data_path()
        if not path or not os.path.isfile(path):
            # Fallback: set simple defaults
            self._set_fallback_defaults()
            return
        try:
            df = pd.read_csv(path)
        except Exception:
            self._set_fallback_defaults()
            return

        # Ensure required columns exist
        needed_cols = []
        for tier, model_col in self.tier_to_model_col.items():
            needed_cols.append(model_col)
            needed_cols.append(model_col + "|total_cost")
        for c in needed_cols:
            if c not in df.columns:
                # Missing expected columns; fallback
                self._set_fallback_defaults()
                return

        # Prepare training corpora per tier globally and per eval_name
        # Also collect costs and correctness per tier
        global_docs = {t: [] for t in self.tiers}
        global_labels = {t: [] for t in self.tiers}
        global_costs = {t: [] for t in self.tiers}
        global_prior_counts = {t: [0, 0] for t in self.tiers}  # [neg, pos]

        per_dataset_docs = defaultdict(lambda: {t: [] for t in self.tiers})
        per_dataset_labels = defaultdict(lambda: {t: [] for t in self.tiers})
        per_dataset_costs = defaultdict(lambda: {t: [] for t in self.tiers})
        per_dataset_priors = defaultdict(lambda: {t: [0, 0] for t in self.tiers})

        # Preprocess prompts and eval_name
        prompts = df.get("prompt", pd.Series([""] * len(df))).fillna("").astype(str).tolist()
        eval_names = df.get("eval_name", pd.Series([""] * len(df))).fillna("").astype(str).tolist()

        # Compute token counts for cost regression: basic tokens only
        token_counts = []
        for p in prompts:
            token_counts.append(len(self.featurizer.basic_tokenize(p)))

        # Iterate rows to build datasets
        for idx in range(len(df)):
            p = prompts[idx]
            en = eval_names[idx]
            tokens = self.featurizer.tokenize(p, en)
            raw_tokens_count = token_counts[idx]

            for tier in self.tiers:
                mcol = self.tier_to_model_col[tier]
                y_val = df.loc[idx, mcol]
                cost_val = df.loc[idx, mcol + "|total_cost"]
                # Validate values
                try:
                    y = int(float(y_val))
                except Exception:
                    continue
                try:
                    cost = float(cost_val)
                    if not (cost >= 0.0):
                        continue
                except Exception:
                    continue

                global_docs[tier].append(tokens)
                global_labels[tier].append(y)
                global_costs[tier].append(cost)
                if y == 1:
                    global_prior_counts[tier][1] += 1
                else:
                    global_prior_counts[tier][0] += 1

                per_dataset_docs[en][tier].append(tokens)
                per_dataset_labels[en][tier].append(y)
                per_dataset_costs[en][tier].append(cost)
                if y == 1:
                    per_dataset_priors[en][tier][1] += 1
                else:
                    per_dataset_priors[en][tier][0] += 1

        # Train global models
        for tier in self.tiers:
            model = MultinomialNB(alpha=1.0)
            if len(global_docs[tier]) >= 5:
                model.fit(global_docs[tier], global_labels[tier])
                self.global_models[tier] = model
            else:
                # No data: empty model yields 0.5 prob
                self.global_models[tier] = MultinomialNB(alpha=1.0)

            # Costs
            if len(global_costs[tier]) > 0:
                self.cost_median[tier] = sorted(global_costs[tier])[len(global_costs[tier]) // 2]
            else:
                self.cost_median[tier] = 0.0

            # Prior correctness
            neg, pos = global_prior_counts[tier]
            total = neg + pos
            if total > 0:
                self.global_prior_correct[tier] = pos / total
            else:
                self.global_prior_correct[tier] = 0.5

        # Dataset-specific models
        for en in per_dataset_docs.keys():
            for tier in self.tiers:
                docs = per_dataset_docs[en][tier]
                labels = per_dataset_labels[en][tier]
                if len(docs) >= 20:
                    m = MultinomialNB(alpha=1.0)
                    m.fit(docs, labels)
                    self.dataset_models[en][tier] = m
                    self.dataset_model_counts[en][tier] = len(docs)
                else:
                    # Not enough data; skip
                    pass
                neg, pos = per_dataset_priors[en][tier]
                total = neg + pos
                if total > 0:
                    self.dataset_prior_correct[en][tier] = pos / total
                else:
                    self.dataset_prior_correct[en][tier] = self.global_prior_correct[tier]

        # Cost regression per tier: y = a + b * token_count
        # We'll use simple OLS; if variance zero, default to median.
        for tier in self.tiers:
            costs = []
            xs = []
            # Build x and y
            # Re-iterate rows to align; this is okay
            for idx in range(len(df)):
                mcol = self.tier_to_model_col[tier]
                cval = df.loc[idx, mcol + "|total_cost"]
                try:
                    y = float(cval)
                    if y < 0:
                        continue
                except Exception:
                    continue
                costs.append(y)
                xs.append(token_counts[idx])
            if len(xs) >= 5 and len(set(xs)) >= 2:
                mean_x = sum(xs) / len(xs)
                mean_y = sum(costs) / len(costs)
                # Compute covariance and variance
                cov = 0.0
                varx = 0.0
                for xi, yi in zip(xs, costs):
                    dx = xi - mean_x
                    cov += dx * (yi - mean_y)
                    varx += dx * dx
                if varx > 0:
                    b = cov / varx
                    a = mean_y - b * mean_x
                    if a < 0:
                        a = 0.0
                    self.cost_regression[tier] = (a, b)
                else:
                    self.cost_regression[tier] = (self.cost_median[tier], 0.0)
            else:
                self.cost_regression[tier] = (self.cost_median[tier], 0.0)

        # Dataset default routes by expected utility
        # Compute mean correctness and mean cost per dataset and tier
        for en, tier_docs in per_dataset_docs.items():
            best_tier = None
            best_score = -1e9
            for tier in self.tiers:
                labels = per_dataset_labels[en][tier]
                costs = per_dataset_costs[en][tier]
                if len(labels) == 0:
                    # Use global priors and median cost
                    mean_acc = self.global_prior_correct.get(tier, 0.5)
                    mean_cost = self.cost_median.get(tier, 0.0)
                else:
                    mean_acc = sum(labels) / len(labels)
                    if len(costs) > 0:
                        mean_cost = sum(costs) / len(costs)
                    else:
                        mean_cost = self.cost_median.get(tier, 0.0)
                score = mean_acc - LAMBDA_COST * mean_cost
                if score > best_score:
                    best_score = score
                    best_tier = tier
            # If something went wrong
            if not best_tier:
                best_tier = "cheap"
            self.dataset_default_route[en] = best_tier

        # Global default
        best_tier = None
        best_score = -1e9
        for tier in self.tiers:
            mean_acc = self.global_prior_correct.get(tier, 0.5)
            mean_cost = self.cost_median.get(tier, 0.0)
            score = mean_acc - LAMBDA_COST * mean_cost
            if score > best_score:
                best_score = score
                best_tier = tier
        if not best_tier:
            best_tier = "cheap"
        self.global_default_route = best_tier

    def _set_fallback_defaults(self):
        # Fallback when reference data is not available
        self.global_models = {t: MultinomialNB(alpha=1.0) for t in self.tiers}
        self.dataset_models = defaultdict(dict)
        self.dataset_model_counts = defaultdict(lambda: defaultdict(int))
        # Reasonable static cost assumptions
        # cheap ~ 2e-5, mid ~ 7e-5, expensive ~ 8.8e-4
        self.cost_median = {
            "cheap": 2.0e-05,
            "mid": 7.0e-05,
            "expensive": 8.8e-04,
        }
        self.cost_regression = {
            "cheap": (2.0e-05, 0.0),
            "mid": (7.0e-05, 0.0),
            "expensive": (8.8e-04, 0.0),
        }
        self.global_prior_correct = {t: 0.5 for t in self.tiers}
        self.global_default_route = "cheap"

    def _estimate_cost(self, tier, n_tokens):
        a, b = self.cost_regression.get(tier, (self.cost_median.get(tier, 0.0), 0.0))
        c = a + b * float(n_tokens)
        if c < 0:
            c = 0.0
        return c

    def _predict_prob_correct(self, tier, tokens, eval_name):
        # Combine dataset-specific and global models by shrinkage weight
        global_model = self.global_models.get(tier)
        if global_model is None:
            return 0.5
        p_global = global_model.predict_proba_correct(tokens)

        p_ds = None
        w = 0.0
        if eval_name in self.dataset_models and tier in self.dataset_models[eval_name]:
            ds_model = self.dataset_models[eval_name][tier]
            p_ds = ds_model.predict_proba_correct(tokens)
            # Use shrinkage weight based on number of samples
            n = self.dataset_model_counts[eval_name].get(tier, 0)
            # Shrinkage constant: around 80 effective samples to blend with global
            K = 80.0
            w = n / (n + K)
            if w > 0.9:
                w = 0.9  # prevent overconfidence
        if p_ds is None:
            return p_global
        p = w * p_ds + (1.0 - w) * p_global
        # Small calibration: pull slightly toward priors to avoid overconfidence
        prior = self.dataset_prior_correct.get(eval_name, {}).get(tier, self.global_prior_correct.get(tier, 0.5))
        p = 0.1 * prior + 0.9 * p
        if p < 1e-6:
            p = 1e-6
        if p > 1 - 1e-6:
            p = 1 - 1e-6
        return p

    def route(self, query, eval_name, candidate_models):
        # Ensure candidate_models contains supported tiers
        cands = [c for c in self.tiers if c in (candidate_models or [])]
        if not cands:
            # Fallback: just return the first candidate if any
            if candidate_models and len(candidate_models) > 0:
                return candidate_models[0]
            else:
                return "cheap"

        # Featurize
        tokens = self.featurizer.tokenize(query or "", eval_name or "")
        n_tokens = len(self.featurizer.basic_tokenize(query or ""))

        # Compute expected utility for each candidate
        utilities = {}
        for tier in cands:
            p_correct = self._predict_prob_correct(tier, tokens, eval_name or "")
            est_cost = self._estimate_cost(tier, n_tokens)
            util = p_correct - LAMBDA_COST * est_cost
            utilities[tier] = util

        # Choose best by expected utility
        best_tier = max(utilities.items(), key=lambda kv: kv[1])[0]

        # Tie-breaker or if utilities are extremely close within epsilon, use dataset default
        sorted_utils = sorted(utilities.values(), reverse=True)
        if len(sorted_utils) >= 2:
            if abs(sorted_utils[0] - sorted_utils[1]) < 1e-4:
                ds_default = self.dataset_default_route.get(eval_name or "", self.global_default_route)
                if ds_default in cands:
                    best_tier = ds_default

        # Safety: if best_tier not in candidate list due to some issue, fallback
        if best_tier not in cands:
            # Try dataset default
            ds_default = self.dataset_default_route.get(eval_name or "", self.global_default_route)
            if ds_default in cands:
                return ds_default
            return cands[0]
        return best_tier

# Global router instance
_GLOBAL_ROUTER = None

def _get_global_router():
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        _GLOBAL_ROUTER = RouterModel()
    return _GLOBAL_ROUTER

class Solution:
    def __init__(self):
        self._router = _get_global_router()

    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        try:
            return self._router.route(query, eval_name, candidate_models)
        except Exception:
            # Fallback: return cheap if available
            if candidate_models and "cheap" in candidate_models:
                return "cheap"
            elif candidate_models:
                return candidate_models[0]
            else:
                return "cheap"