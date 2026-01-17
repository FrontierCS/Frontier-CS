import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
import joblib
import re

class Solution:
    def __init__(self):
        # Load and preprocess reference data
        self.model_mapping = None
        self.clf = None
        self.tier_encoder = None
        self.eval_encoder = None
        self._initialize_model()
    
    def _initialize_model(self):
        # Try to load cached model first
        cache_path = "model_cache.pkl"
        if os.path.exists(cache_path):
            try:
                self._load_cached_model(cache_path)
                return
            except:
                pass
        
        # Build model from scratch
        self._build_model()
        
        # Cache the model
        self._save_model(cache_path)
    
    def _load_cached_model(self, cache_path):
        cached_data = joblib.load(cache_path)
        self.clf = cached_data['clf']
        self.model_mapping = cached_data['model_mapping']
        self.tier_encoder = cached_data['tier_encoder']
        self.eval_encoder = cached_data['eval_encoder']
    
    def _save_model(self, cache_path):
        cached_data = {
            'clf': self.clf,
            'model_mapping': self.model_mapping,
            'tier_encoder': self.tier_encoder,
            'eval_encoder': self.eval_encoder
        }
        joblib.dump(cached_data, cache_path, compress=3)
    
    def _build_model(self):
        # Load reference data
        data_path = "resources/reference_data.csv"
        if not os.path.exists(data_path):
            # Try alternative path
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "resources", "reference_data.csv"
            )
        
        df = pd.read_csv(data_path)
        
        # Extract features and labels
        X, y = self._prepare_training_data(df)
        
        # Train model
        self._train_classifier(X, y)
    
    def _prepare_training_data(self, df):
        # Clean and prepare prompts
        df['prompt_clean'] = df['prompt'].apply(self._clean_text)
        
        # Extract oracle choices and map to tiers
        oracle_models = df['oracle_model_to_route_to'].values
        
        # Learn mapping from concrete models to routing tiers
        self.model_mapping = self._learn_model_mapping(df)
        
        # Map oracle models to tiers
        tier_labels = []
        for model in oracle_models:
            tier = self._map_model_to_tier(model)
            tier_labels.append(tier)
        
        # Prepare features
        X = pd.DataFrame({
            'prompt': df['prompt_clean'],
            'eval_name': df['eval_name'],
            'prompt_length': df['prompt'].str.len(),
            'has_code': df['prompt'].apply(lambda x: int('def ' in str(x) or 'import ' in str(x))),
            'question_count': df['prompt'].apply(lambda x: str(x).count('?')),
            'has_options': df['prompt'].apply(lambda x: int('A)' in str(x) or 'B)' in str(x)))
        })
        
        # Encode tiers
        self.tier_encoder = LabelEncoder()
        y = self.tier_encoder.fit_transform(tier_labels)
        
        # Encode eval names
        self.eval_encoder = LabelEncoder()
        X['eval_encoded'] = self.eval_encoder.fit_transform(X['eval_name'])
        
        return X, y
    
    def _learn_model_mapping(self, df):
        # Analyze model performance to create tier mapping
        model_cols = [col for col in df.columns if '|' not in col and col not in 
                     ['sample_id', 'prompt', 'eval_name', 'oracle_model_to_route_to']]
        
        model_stats = []
        for model in model_cols:
            # Get cost column
            cost_col = f"{model}|total_cost"
            if cost_col not in df.columns:
                continue
            
            # Calculate statistics
            avg_cost = df[cost_col].mean()
            avg_acc = df[model].mean()
            model_stats.append({
                'model': model,
                'avg_cost': avg_cost,
                'avg_acc': avg_acc
            })
        
        # Sort by cost and create tiers
        model_stats.sort(key=lambda x: x['avg_cost'])
        n_models = len(model_stats)
        
        mapping = {}
        for i, stat in enumerate(model_stats):
            if i < n_models // 3:
                mapping[stat['model']] = 'cheap'
            elif i < 2 * n_models // 3:
                mapping[stat['model']] = 'mid'
            else:
                mapping[stat['model']] = 'expensive'
        
        return mapping
    
    def _map_model_to_tier(self, model):
        # Try exact match first
        if model in self.model_mapping:
            return self.model_mapping[model]
        
        # Try to find best match
        for key in self.model_mapping:
            if model in key or key in model:
                return self.model_mapping[key]
        
        # Default to mid if no match found
        return 'mid'
    
    def _clean_text(self, text):
        if pd.isna(text):
            return ""
        text = str(text)
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\?\.\,]', ' ', text)
        return text.strip()
    
    def _train_classifier(self, X, y):
        # Create preprocessing pipeline
        text_transformer = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                min_df=2,
                max_df=0.8,
                ngram_range=(1, 2),
                stop_words='english'
            ))
        ])
        
        numeric_transformer = Pipeline([
            ('scaler', 'passthrough')
        ])
        
        preprocessor = ColumnTransformer([
            ('text', text_transformer, 'prompt'),
            ('numeric', numeric_transformer, ['prompt_length', 'has_code', 'question_count', 'has_options', 'eval_encoded'])
        ])
        
        # Create full pipeline
        self.clf = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', RandomForestClassifier(
                n_estimators=100,
                max_depth=20,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
                class_weight='balanced'
            ))
        ])
        
        # Train
        self.clf.fit(X, y)
    
    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        # Clean query
        query_clean = self._clean_text(query)
        
        # Prepare features for prediction
        features = pd.DataFrame([{
            'prompt': query_clean,
            'eval_name': eval_name,
            'prompt_length': len(query),
            'has_code': int('def ' in query or 'import ' in query),
            'question_count': query.count('?'),
            'has_options': int('A)' in query or 'B)' in query)
        }])
        
        # Encode eval name if known, otherwise use default
        if hasattr(self.eval_encoder, 'classes_'):
            try:
                features['eval_encoded'] = self.eval_encoder.transform([eval_name])[0]
            except:
                features['eval_encoded'] = -1
        else:
            features['eval_encoded'] = -1
        
        # Predict tier
        if self.clf is not None:
            try:
                pred_idx = self.clf.predict(features)[0]
                if hasattr(self.tier_encoder, 'classes_'):
                    predicted_tier = self.tier_encoder.inverse_transform([pred_idx])[0]
                else:
                    predicted_tier = candidate_models[pred_idx % len(candidate_models)]
            except:
                # Fallback: use simple heuristics
                predicted_tier = self._fallback_heuristic(query, eval_name, candidate_models)
        else:
            predicted_tier = self._fallback_heuristic(query, eval_name, candidate_models)
        
        # Ensure prediction is in candidate models
        if predicted_tier in candidate_models:
            return predicted_tier
        else:
            # Return cheapest option as fallback
            return candidate_models[0]
    
    def _fallback_heuristic(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        # Simple rule-based fallback
        query_lower = query.lower()
        
        # Check for complex indicators
        complex_indicators = [
            'explain', 'why', 'how', 'analyze', 'compare', 'contrast',
            'mathematical', 'calculate', 'derive', 'prove'
        ]
        
        # Check for simple indicators
        simple_indicators = [
            'yes/no', 'true/false', 'multiple choice', 'A)', 'B)', 'C)', 'D)'
        ]
        
        # Check query length and complexity
        if len(query) > 500:
            # Long queries often need better models
            return candidate_models[-1] if len(candidate_models) > 0 else 'expensive'
        
        # Check for code
        if 'def ' in query or 'import ' in query or 'function' in query_lower:
            # Code questions often need mid-level models
            mid_idx = len(candidate_models) // 2
            return candidate_models[mid_idx] if len(candidate_models) > mid_idx else 'mid'
        
        # Check for complex questions
        if any(indicator in query_lower for indicator in complex_indicators):
            return candidate_models[-1] if len(candidate_models) > 0 else 'expensive'
        
        # Check for simple questions
        if any(indicator in query_lower for indicator in simple_indicators):
            return candidate_models[0] if len(candidate_models) > 0 else 'cheap'
        
        # Default to mid
        mid_idx = len(candidate_models) // 2
        return candidate_models[mid_idx] if len(candidate_models) > mid_idx else 'mid'