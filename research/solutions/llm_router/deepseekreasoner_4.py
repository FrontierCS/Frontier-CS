import os
import pandas as pd
import numpy as np
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import re
import joblib

class Solution:
    def __init__(self):
        # Try multiple possible paths for the reference data
        possible_paths = [
            "resources/reference_data.csv",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                        "resources", "reference_data.csv"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "reference_data.csv")
        ]
        
        self.df = None
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    self.df = pd.read_csv(path)
                    break
                except:
                    continue
        
        if self.df is None:
            # Fallback: create empty structure
            self.model = None
            self.tier_mapping = None
            return
        
        # Preprocess data
        self._prepare_data()
        
        # Train model
        self._train_model()
    
    def _prepare_data(self):
        """Prepare training data from reference dataset"""
        if self.df is None:
            return
            
        # Identify model columns (those without '|' in name)
        model_cols = [col for col in self.df.columns 
                     if '|' not in col and col not in 
                     ['sample_id', 'prompt', 'eval_name', 'oracle_model_to_route_to']]
        
        # Create tier mapping based on average costs
        model_costs = {}
        for model in model_cols:
            cost_col = f"{model}|total_cost"
            if cost_col in self.df.columns:
                # Use median cost to be robust to outliers
                valid_costs = self.df[cost_col].dropna()
                if len(valid_costs) > 0:
                    model_costs[model] = np.median(valid_costs)
        
        # Sort models by cost and assign to tiers
        sorted_models = sorted(model_costs.items(), key=lambda x: x[1])
        n = len(sorted_models)
        
        # Create tier mapping
        self.tier_mapping = {}
        for i, (model, _) in enumerate(sorted_models):
            if i < n // 3:
                self.tier_mapping[model] = 'cheap'
            elif i < 2 * n // 3:
                self.tier_mapping[model] = 'mid'
            else:
                self.tier_mapping[model] = 'expensive'
        
        # For each sample, determine best tier based on oracle model
        self.df['oracle_tier'] = self.df['oracle_model_to_route_to'].map(self.tier_mapping)
        
        # Prepare features
        self.df['text'] = self.df['eval_name'] + ' ' + self.df['prompt'].astype(str)
        
        # Clean text
        self.df['text'] = self.df['text'].apply(self._clean_text)
    
    def _clean_text(self, text):
        """Clean and normalize text"""
        if not isinstance(text, str):
            return ""
        # Replace newline markers with space
        text = text.replace('\\n', ' ')
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_features(self, text):
        """Extract heuristic features from text"""
        features = {}
        text_lower = text.lower()
        
        # Length features
        features['char_count'] = len(text)
        features['word_count'] = len(text.split())
        
        # Question indicators
        features['has_question_mark'] = int('?' in text)
        features['has_explain'] = int('explain' in text_lower)
        features['has_why'] = int('why' in text_lower)
        features['has_how'] = int('how' in text_lower)
        features['has_what'] = int('what' in text_lower)
        
        # Code-related features
        features['has_code'] = int(any(word in text_lower for word in 
                                     ['code', 'function', 'def ', 'class ', 'import', 'print']))
        
        # Multiple choice indicators
        features['has_choices'] = int(any(marker in text for marker in 
                                         ['A)', 'B)', 'C)', 'D)', 'A.', 'B.', 'C.', 'D.']))
        
        # Complexity indicators
        features['has_technical'] = int(any(word in text_lower for word in 
                                          ['algorithm', 'complexity', 'recursive', 'optimize']))
        
        return features
    
    def _train_model(self):
        """Train the routing model"""
        if self.df is None or len(self.df) == 0:
            return
            
        # Use a simple heuristic + ML approach
        # First, extract heuristic features
        X_heuristic = []
        for text in self.df['text']:
            features = self._extract_features(text)
            X_heuristic.append(list(features.values()))
        
        # Combine with TF-IDF features
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        
        # Create pipeline
        self.model = Pipeline([
            ('tfidf', vectorizer),
            ('clf', LogisticRegression(
                random_state=42,
                max_iter=1000,
                class_weight='balanced'
            ))
        ])
        
        # Train
        X_text = self.df['text'].fillna('').tolist()
        y = self.df['oracle_tier'].fillna('mid').tolist()
        
        if len(set(y)) >= 2:  # Need at least 2 classes
            self.model.fit(X_text, y)
        else:
            self.model = None
    
    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        # Default fallback
        if not candidate_models:
            return "mid"
        
        # Combine query with eval_name for context
        text = eval_name + ' ' + str(query)
        text = self._clean_text(text)
        
        # Extract heuristic features
        features = self._extract_features(text)
        
        # Simple rule-based fallback based on heuristics
        word_count = features['word_count']
        has_choices = features['has_choices']
        has_technical = features['has_technical']
        has_code = features['has_code']
        
        # If no model or heuristic suggests simple query
        if self.model is None:
            if word_count < 20 and has_choices and not has_technical:
                return 'cheap'
            elif has_code or has_technical or word_count > 100:
                return 'expensive'
            else:
                return 'mid'
        
        # Use trained model if available
        try:
            prediction = self.model.predict([text])[0]
            if prediction in candidate_models:
                return prediction
        except:
            pass
        
        # Fallback heuristics
        if word_count < 20 and has_choices and not has_technical:
            return 'cheap'
        elif word_count > 100 or has_code or has_technical:
            return 'expensive'
        else:
            return 'mid'