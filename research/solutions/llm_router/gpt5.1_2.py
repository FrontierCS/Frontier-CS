import os
import math
import re

try:
    import pandas as pd
except Exception:
    pd = None

TIER_NAMES = ["cheap", "mid", "expensive"]
TIER_TO_MODEL = {
    "cheap": "mistralai/mistral-7b-chat",
    "mid": "mistralai/mixtral-8x7b-chat",
    "expensive": "gpt-4-1106-preview",
}
LAMBDA_COST = 150.0
WORD_RE = re.compile(r"[A-Za-z0-9]+")

_router = None


class _NaiveBayesRouter:
    def __init__(self):
        self.classes = list(TIER_NAMES)
        self.token_counts = {c: {} for c in self.classes}
        self.class_token_counts = {c: 0 for c in self.classes}
        self.class_doc_counts = {c: 0 for c in self.classes}
        self.vocab = set()
        self.max_vocab_size = 100000
        self.max_tokens_main = 96
        self.alpha_word = 1.0
        self.alpha_prior = 1.0
        self.vocab_size = 0
        self.num_docs = 0
        self.log_priors = {}
        self.trained = False

        if pd is None:
            return

        df = self._load_reference_dataframe()
        if df is None:
            return

        self._train_from_dataframe(df)

    def _load_reference_dataframe(self):
        if pd is None:
            return None

        possible_paths = []
        try:
            current_file = os.path.abspath(__file__)
            base_dir = os.path.dirname(current_file)
            possible_paths.append(
                os.path.join(os.path.dirname(base_dir), "resources", "reference_data.csv")
            )
            possible_paths.append(os.path.join(base_dir, "resources", "reference_data.csv"))
        except Exception:
            pass
        possible_paths.append(os.path.join("resources", "reference_data.csv"))

        data_path = None
        for p in possible_paths:
            if os.path.exists(p):
                data_path = p
                break

        if data_path is None:
            return None

        required_cols = ["prompt", "eval_name"]
        for model in TIER_TO_MODEL.values():
            required_cols.append(model)
            required_cols.append(model + "|total_cost")

        try:
            df = pd.read_csv(data_path, usecols=required_cols)
        except Exception:
            try:
                df = pd.read_csv(data_path)
                if not all(col in df.columns for col in required_cols):
                    return None
                df = df[required_cols]
            except Exception:
                return None

        return df

    def _train_from_dataframe(self, df):
        columns = list(df.columns)
        idx_map = {name: idx for idx, name in enumerate(columns)}

        try:
            isna = pd.isna
        except Exception:
            def isna(x):
                return x is None or (isinstance(x, float) and math.isnan(x))

        it = df.itertuples(index=False, name=None)
        for row in it:
            prompt = row[idx_map["prompt"]]
            eval_name = row[idx_map["eval_name"]] if "eval_name" in idx_map else ""

            best_tier = None
            best_score = None
            for tier, model in TIER_TO_MODEL.items():
                idx_acc = idx_map.get(model)
                idx_cost = idx_map.get(model + "|total_cost")
                if idx_acc is None or idx_cost is None:
                    continue
                acc = row[idx_acc]
                cost = row[idx_cost]
                if isna(acc) or isna(cost):
                    continue
                try:
                    acc_f = float(acc)
                    cost_f = float(cost)
                except Exception:
                    continue
                score = acc_f - LAMBDA_COST * cost_f
                if (best_tier is None) or (score > best_score):
                    best_score = score
                    best_tier = tier

            if best_tier is None:
                continue

            tokens = self._tokenize(prompt, eval_name)
            if not tokens:
                continue
            self._update_counts(best_tier, tokens)

        self.vocab_size = len(self.vocab)
        self.num_docs = sum(self.class_doc_counts.values())
        if self.vocab_size == 0 or self.num_docs == 0:
            self.trained = False
            return

        denom_prior = self.num_docs + self.alpha_prior * len(self.classes)
        for c in self.classes:
            num = self.class_doc_counts[c] + self.alpha_prior
            self.log_priors[c] = math.log(num / denom_prior)

        self.trained = True
        try:
            del df
        except Exception:
            pass

    def _basic_tokenize(self, text):
        if not isinstance(text, str):
            text = "" if text is None else str(text)
        tokens = WORD_RE.findall(text.lower())
        if len(tokens) > self.max_tokens_main:
            tokens = tokens[: self.max_tokens_main]
        return tokens

    def _tokenize(self, prompt, eval_name):
        tokens = self._basic_tokenize(prompt)

        try:
            if eval_name is None:
                ev = "unknown"
            else:
                ev = str(eval_name).lower()
        except Exception:
            ev = "unknown"
        tokens.append("__eval__" + ev)

        length = len(tokens)
        if length <= 30:
            bucket = "0"
        elif length <= 100:
            bucket = "1"
        elif length <= 250:
            bucket = "2"
        else:
            bucket = "3"
        tokens.append("__len__" + bucket)

        return tokens

    def _update_counts(self, label, tokens):
        if label not in self.classes:
            return
        self.class_doc_counts[label] += 1
        token_counts_label = self.token_counts[label]
        for t in tokens:
            if t in self.vocab:
                token_counts_label[t] = token_counts_label.get(t, 0) + 1
                self.class_token_counts[label] += 1
            else:
                if len(self.vocab) >= self.max_vocab_size:
                    continue
                self.vocab.add(t)
                token_counts_label[t] = token_counts_label.get(t, 0) + 1
                self.class_token_counts[label] += 1

    def predict(self, query, eval_name, candidate_models):
        if not candidate_models:
            return None

        cand_classes = [c for c in self.classes if c in candidate_models]
        if not self.trained or not cand_classes:
            for name in ("cheap", "mid", "expensive"):
                if name in candidate_models:
                    return name
            return candidate_models[0]

        tokens = self._tokenize(query, eval_name)
        best_class = None
        best_logprob = None
        V = self.vocab_size
        alpha = self.alpha_word

        for c in cand_classes:
            logprob = self.log_priors.get(c, 0.0)
            token_counts_label = self.token_counts[c]
            denom = self.class_token_counts[c] + alpha * V

            if denom > 0.0:
                for t in tokens:
                    if t not in self.vocab:
                        continue
                    count = token_counts_label.get(t, 0)
                    prob = (count + alpha) / denom
                    logprob += math.log(prob)

            if (best_class is None) or (logprob > best_logprob):
                best_logprob = logprob
                best_class = c

        if best_class is None:
            for name in ("cheap", "mid", "expensive"):
                if name in candidate_models:
                    return name
            return candidate_models[0]

        return best_class


class Solution:
    def __init__(self):
        global _router
        if _router is None:
            _router = _NaiveBayesRouter()

    def solve(self, query, eval_name, candidate_models):
        if not candidate_models:
            return "cheap"
        global _router
        if _router is None:
            _router = _NaiveBayesRouter()
        choice = _router.predict(query, eval_name, candidate_models)
        if choice in candidate_models:
            return choice
        for name in ("cheap", "mid", "expensive"):
            if name in candidate_models:
                return name
        return candidate_models[0]