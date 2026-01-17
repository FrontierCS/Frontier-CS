import math
import os
import re
from collections import defaultdict, Counter

import pandas as pd


TOKEN_PATTERN = re.compile(r"[A-Za-z_]+")


def _tokenize(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.lower()
    return TOKEN_PATTERN.findall(text)


class NaiveBayesRouter:
    def __init__(self, class_labels, log_class_priors, word_log_probs, unk_log_probs):
        self.class_labels = class_labels
        self.log_class_priors = log_class_priors
        self.word_log_probs = word_log_probs
        self.unk_log_probs = unk_log_probs
        self.num_classes = len(class_labels)

    @staticmethod
    def from_dataframe(df, lambda_cost=150.0):
        # Define mapping from routing tiers to concrete models in the reference data
        tier_labels = ["cheap", "mid", "expensive"]
        tier_to_model = {
            "cheap": "mistralai/mistral-7b-chat",
            "mid": "mistralai/mixtral-8x7b-chat",
            "expensive": "gpt-4-1106-preview",
        }

        # Basic column checks
        if "prompt" not in df.columns or "eval_name" not in df.columns:
            return None

        for tier, model_name in tier_to_model.items():
            correct_col = model_name
            cost_col = f"{model_name}|total_cost"
            if correct_col not in df.columns or cost_col not in df.columns:
                return None

        docs_tokens = []
        labels = []

        for _, row in df.iterrows():
            prompt = row.get("prompt", "")
            eval_name = row.get("eval_name", "")

            # Ensure string
            if not isinstance(prompt, str):
                prompt = str(prompt)
            if not isinstance(eval_name, str):
                eval_name = str(eval_name)

            best_reward = None
            best_tier_idx = None
            best_cost = None

            for tier_idx, tier in enumerate(tier_labels):
                model_name = tier_to_model[tier]
                correct_val = row.get(model_name)
                cost_val = row.get(f"{model_name}|total_cost")

                if pd.isna(correct_val) or pd.isna(cost_val):
                    best_reward = None
                    best_tier_idx = None
                    best_cost = None
                    break

                try:
                    correct_f = float(correct_val)
                    cost_f = float(cost_val)
                except Exception:
                    best_reward = None
                    best_tier_idx = None
                    best_cost = None
                    break

                reward = correct_f - lambda_cost * cost_f

                if best_reward is None:
                    best_reward = reward
                    best_tier_idx = tier_idx
                    best_cost = cost_f
                else:
                    if reward > best_reward:
                        best_reward = reward
                        best_tier_idx = tier_idx
                        best_cost = cost_f
                    elif reward == best_reward and cost_f < best_cost:
                        best_reward = reward
                        best_tier_idx = tier_idx
                        best_cost = cost_f

            if best_tier_idx is None:
                continue

            tokens = _tokenize(prompt) + _tokenize(eval_name)
            docs_tokens.append(tokens)
            labels.append(best_tier_idx)

        if not docs_tokens or not labels:
            return None

        return _train_naive_bayes(docs_tokens, labels, tier_labels)

    def predict(self, query, eval_name):
        query_text = "" if query is None else str(query)
        eval_text = "" if eval_name is None else str(eval_name)
        tokens = _tokenize(query_text) + _tokenize(eval_text)

        if not tokens:
            # Fallback to class with highest prior
            best_idx = 0
            best_val = self.log_class_priors[0]
            for i in range(1, self.num_classes):
                if self.log_class_priors[i] > best_val:
                    best_val = self.log_class_priors[i]
                    best_idx = i
            return self.class_labels[best_idx]

        counts = Counter(tokens)
        scores = list(self.log_class_priors)

        for token, tf in counts.items():
            arr = self.word_log_probs.get(token)
            if arr is None:
                for c in range(self.num_classes):
                    scores[c] += tf * self.unk_log_probs[c]
            else:
                for c in range(self.num_classes):
                    scores[c] += tf * arr[c]

        best_idx = 0
        best_score = scores[0]
        for i in range(1, self.num_classes):
            if scores[i] > best_score:
                best_score = scores[i]
                best_idx = i

        return self.class_labels[best_idx]


def _train_naive_bayes(docs_tokens, labels, class_labels):
    num_classes = len(class_labels)
    class_doc_counts = [0] * num_classes
    class_word_counts = [defaultdict(int) for _ in range(num_classes)]
    total_words = [0] * num_classes
    vocab = set()

    for tokens, label in zip(docs_tokens, labels):
        if label < 0 or label >= num_classes:
            continue
        class_doc_counts[label] += 1
        for tok in tokens:
            class_word_counts[label][tok] += 1
            total_words[label] += 1
            vocab.add(tok)

    num_docs = sum(class_doc_counts)
    if num_docs == 0 or not vocab:
        return None

    alpha = 1.0
    class_alpha = 1.0
    vocab_size = len(vocab)

    log_class_priors = []
    denom_docs = num_docs + class_alpha * num_classes
    for c in range(num_classes):
        log_class_priors.append(math.log((class_doc_counts[c] + class_alpha) / denom_docs))

    log_denoms = []
    for c in range(num_classes):
        denom = total_words[c] + alpha * vocab_size
        log_denoms.append(math.log(denom))

    word_log_probs = {}
    for word in vocab:
        arr = []
        for c in range(num_classes):
            count_cw = class_word_counts[c].get(word, 0)
            arr.append(math.log(count_cw + alpha) - log_denoms[c])
        word_log_probs[word] = arr

    unk_log_probs = [math.log(alpha) - log_denoms[c] for c in range(num_classes)]

    return NaiveBayesRouter(class_labels, log_class_priors, word_log_probs, unk_log_probs)


_GLOBAL_ROUTER = None
_LOAD_ATTEMPTED = False

COST_RANK = {"cheap": 0, "mid": 1, "expensive": 2}


def _load_model():
    global _GLOBAL_ROUTER, _LOAD_ATTEMPTED
    if _LOAD_ATTEMPTED:
        return
    _LOAD_ATTEMPTED = True

    try:
        data_path = "resources/reference_data.csv"
        if not os.path.exists(data_path):
            try:
                problem_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                alt_path = os.path.join(problem_dir, "resources", "reference_data.csv")
                if os.path.exists(alt_path):
                    data_path = alt_path
            except Exception:
                pass

        if not os.path.exists(data_path):
            _GLOBAL_ROUTER = None
            return

        df = pd.read_csv(data_path)
        router = NaiveBayesRouter.from_dataframe(df)
        _GLOBAL_ROUTER = router
    except Exception:
        _GLOBAL_ROUTER = None


def _get_model():
    if not _LOAD_ATTEMPTED:
        _load_model()
    return _GLOBAL_ROUTER


def choose_closest_available(desired_label, candidate_models):
    if not candidate_models:
        return "cheap"

    desired_rank = COST_RANK.get(desired_label)
    if desired_rank is None:
        for label in ["cheap", "mid", "expensive"]:
            if label in candidate_models:
                return label
        return candidate_models[0]

    best_candidate = None
    best_score = None

    for cand in candidate_models:
        r = COST_RANK.get(cand)
        if r is None:
            continue
        score = (abs(r - desired_rank), r)  # prefer closer; tie-break by cheaper
        if best_score is None or score < best_score:
            best_score = score
            best_candidate = cand

    if best_candidate is not None:
        return best_candidate

    return candidate_models[0]


def fallback_router(query, eval_name, candidate_models):
    for label in ["cheap", "mid", "expensive"]:
        if label in candidate_models:
            return label
    return candidate_models[0] if candidate_models else "cheap"


class Solution:
    def __init__(self):
        _load_model()

    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        model = _get_model()
        if model is None:
            return fallback_router(query, eval_name, candidate_models)

        predicted = model.predict(query, eval_name)
        if predicted in candidate_models:
            return predicted

        return choose_closest_available(predicted, candidate_models)