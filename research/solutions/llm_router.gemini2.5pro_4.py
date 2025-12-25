import pandas as pd
import ast
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

class Solution:
    """
    An expert programmer's solution to the LLM Router problem.
    This solution trains a machine learning pipeline to predict the optimal
    routing tier ('cheap', 'mid', 'expensive') for a given query.

    The strategy involves:
    1.  **Offline Training**: In the `__init__` method, a classification model is
        trained on the provided reference dataset.
    2.  **Label Generation**: For each query in the reference data, the optimal
        routing tier is determined by calculating a score for each tier:
        `score = correctness - (lambda * cost)`. The tier with the highest
        score is chosen as the label for that query. This leverages the provided
        example mapping of tiers to concrete LLMs and the given scoring formula.
    3.  **Feature Engineering**:
        - The input `query` text is converted into a high-dimensional sparse
          vector using TF-IDF with n-grams to capture textual patterns.
        - The `eval_name` is treated as a categorical feature and is one-hot
          encoded to allow the model to learn task-specific routing policies.
          The base name of the task is extracted for better generalization.
    4.  **Model Selection**: A `SGDClassifier` with `log_loss` (effectively a
        fast, scalable Logistic Regression model) is used. It's well-suited for
        high-dimensional text data and is computationally efficient, fitting
        the CPU-only environment. `class_weight='balanced'` is used to handle
        potential imbalance in the generated labels.
    5.  **Pipeline**: All preprocessing and classification steps are encapsulated
        in a scikit-learn `Pipeline`. This ensures proper data handling and
        makes the prediction step in `solve` clean and simple.
    6.  **Inference**: The `solve` method uses the pre-trained pipeline to
        predict the best tier for new, unseen queries based on their text and
        `eval_name`. It's stateless and fast, meeting the problem's constraints.
    """
    def __init__(self):
        self.pipeline = None
        self._train()

    def _train(self):
        dataset_paths = ["/data/reference_dataset.csv", "reference_dataset.csv"]
        
        df = None
        for path in dataset_paths:
            try:
                df = pd.read_csv(path)
                break
            except FileNotFoundError:
                continue
        
        if df is None:
            self.pipeline = None
            return

        def process_prompt(p_str):
            try:
                p_list = ast.literal_eval(p_str)
                if isinstance(p_list, list):
                    return ' '.join(map(str, p_list))
            except (ValueError, SyntaxError):
                pass
            return str(p_str)

        df['prompt_processed'] = df['prompt'].apply(process_prompt)
        df['eval_name_base'] = df['eval_name'].apply(lambda x: x.split('.')[0])

        MODEL_MAPPING = {
            "cheap": "mistralai/mistral-7b-chat",
            "mid": "mistralai/mixtral-8x7b-chat",
            "expensive": "gpt-4-1106-preview",
        }
        LAMBDA = 150.0

        scores = pd.DataFrame(index=df.index)
        for tier, model_name in MODEL_MAPPING.items():
            correctness_col = model_name
            cost_col = f"{model_name}|total_cost"
            
            if correctness_col in df.columns and cost_col in df.columns:
                correctness = pd.to_numeric(df[correctness_col], errors='coerce').fillna(0.0)
                cost = pd.to_numeric(df[cost_col], errors='coerce').fillna(0.0)
                scores[tier] = correctness - LAMBDA * cost
            else:
                scores[tier] = -np.inf
        
        df['label'] = scores.idxmax(axis=1)

        X = df[['prompt_processed', 'eval_name_base']]
        y = df['label']

        preprocessor = ColumnTransformer(
            transformers=[
                ('text', TfidfVectorizer(
                    ngram_range=(1, 2), 
                    min_df=2, 
                    max_df=0.9, 
                    max_features=35000, 
                    stop_words='english',
                    token_pattern=r'(?u)\b\w\w+\b'
                 ), 'prompt_processed'),
                ('cat', OneHotEncoder(handle_unknown='ignore'), ['eval_name_base'])
            ],
            remainder='drop'
        )
        
        self.pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', SGDClassifier(
                loss='log_loss', 
                penalty='elasticnet', 
                alpha=1e-5, 
                class_weight='balanced',
                random_state=42, 
                max_iter=1000, 
                tol=1e-3,
                n_jobs=-1
            ))
        ])

        self.pipeline.fit(X, y)

    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        """
        Select exactly one routing option for the given query.

        Args:
            query: The user query.
            eval_name: The dataset or task name (e.g., "mbpp").
            candidate_models: A list of available routing options 
                              (["cheap", "mid", "expensive"] by default).

        Returns:
            A single string from candidate_models indicating the chosen model.
        """
        if self.pipeline is None:
            return "cheap"

        eval_name_base = eval_name.split('.')[0]
        
        test_df = pd.DataFrame([{'prompt_processed': query, 'eval_name_base': eval_name_base}])
        
        try:
            prediction = self.pipeline.predict(test_df)
            chosen_model = prediction[0]
        except Exception:
            # Fallback in case of any prediction error
            chosen_model = "cheap"

        if chosen_model in candidate_models:
            return chosen_model
        else:
            if "cheap" in candidate_models:
                return "cheap"
            return candidate_models[0]
