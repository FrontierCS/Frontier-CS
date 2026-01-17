import pandas as pd
import numpy as np
import re
import os
from collections import defaultdict
from typing import Dict, List, Tuple
import hashlib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

class Solution:
    def __init__(self):
        self.trained = False
        self.vectorizer = None
        self.models = {}
        self.label_encoder = LabelEncoder()
        self.eval_stats = {}
        self.candidate_mapping = {}
        
    def load_reference_data(self):
        """Load and preprocess reference data"""
        try:
            data_path = "resources/reference_data.csv"
            if not os.path.exists(data_path):
                data_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "resources", "reference_data.csv"
                )
            
            df = pd.read_csv(data_path)
            
            # Extract model columns
            model_cols = [col for col in df.columns if '|' not in col and 
                         col not in ['sample_id', 'prompt', 'eval_name', 'oracle_model_to_route_to']]
            
            # Process each row
            train_data = []
            for _, row in df.iterrows():
                prompt = str(row['prompt']).replace('\\n', '\n')
                eval_name = str(row['eval_name'])
                
                # Calculate utility for each model
                model_utils = {}
                for model in model_cols:
                    correct = float(row[model])
                    cost = float(row[f"{model}|total_cost"])
                    utility = correct - 150.0 * cost
                    model_utils[model] = utility
                
                # Find best model
                best_model = max(model_utils.items(), key=lambda x: x[1])[0]
                oracle_model = str(row.get('oracle_model_to_route_to', best_model))
                
                train_data.append({
                    'prompt': prompt,
                    'eval_name': eval_name,
                    'best_model': oracle_model
                })
            
            return train_data
            
        except Exception as e:
            # Fallback: generate synthetic training patterns
            return self._generate_synthetic_data()
    
    def _generate_synthetic_data(self):
        """Generate synthetic training data based on query characteristics"""
        synthetic_data = []
        patterns = [
            (r'(?i)(code|program|function|algorithm|debug)', 'programming'),
            (r'(?i)(math|calculate|equation|formula|derivative)', 'math'),
            (r'(?i)(history|century|war|king|queen|ancient)', 'history'),
            (r'(?i)(science|physics|chemistry|biology|experiment)', 'science'),
            (r'(?i)(translate|language|word|sentence|grammar)', 'language'),
            (r'(?i)(philosophy|ethics|moral|theory|argument)', 'philosophy'),
            (r'(?i)(economic|market|business|finance|stock)', 'economics'),
            (r'(?i)(legal|law|court|contract|rights)', 'law'),
        ]
        
        # Generate synthetic queries for each pattern
        for pattern, category in patterns:
            for i in range(10):
                query = f"Example {category} query {i}"
                # Assign model based on complexity pattern
                if 'programming' in category or 'math' in category:
                    best = 'gpt-4-1106-preview'
                elif 'science' in category or 'law' in category:
                    best = 'claude-v2'
                else:
                    best = 'mistralai/mixtral-8x7b-chat'
                
                synthetic_data.append({
                    'prompt': query,
                    'eval_name': 'synthetic',
                    'best_model': best
                })
        
        return synthetic_data
    
    def extract_features(self, text):
        """Extract features from query text"""
        text_lower = text.lower()
        
        # Length features
        features = {
            'length': min(len(text), 1000) / 1000.0,
            'word_count': len(text.split()),
            'has_code': 1.0 if any(x in text_lower for x in ['def ', 'function', 'import ', 'print(']) else 0.0,
            'has_math': 1.0 if any(x in text_lower for x in ['calculate', 'equation', 'solve for', 'derivative']) else 0.0,
            'has_question': 1.0 if '?' in text else 0.0,
            'has_quote': 1.0 if '"' in text or "'" in text else 0.0,
            'has_multiple_choice': 1.0 if re.search(r'[A-D]\)', text) else 0.0,
            'has_explanation': 1.0 if any(x in text_lower for x in ['explain', 'why', 'how', 'describe']) else 0.0,
            'complexity_score': min(len(text.split()) / 50.0, 1.0)
        }
        
        # Complexity estimate
        complex_words = sum(1 for word in text_lower.split() if len(word) > 8)
        features['complex_words_ratio'] = complex_words / max(len(text_lower.split()), 1)
        
        return features
    
    def cluster_models(self, train_data):
        """Cluster models into cheap/mid/expensive tiers"""
        model_categories = {}
        
        # Known model patterns for clustering
        cheap_patterns = ['mistral-7b', '7b', '13b', 'llama-2-13b', 'WizardLM-13B']
        mid_patterns = ['mixtral', '8x7b', '34b', 'llama-2-70b', 'Yi-34B', 'claude-instant']
        expensive_patterns = ['gpt-4', 'claude-v2', 'claude-v1', 'gpt-3.5-turbo']
        
        all_models = list(set([d['best_model'] for d in train_data]))
        
        for model in all_models:
            model_lower = model.lower()
            
            if any(pattern in model_lower for pattern in expensive_patterns):
                model_categories[model] = 'expensive'
            elif any(pattern in model_lower for pattern in mid_patterns):
                model_categories[model] = 'mid'
            elif any(pattern in model_lower for pattern in cheap_patterns):
                model_categories[model] = 'cheap'
            else:
                # Default to mid for unknown models
                model_categories[model] = 'mid'
        
        return model_categories
    
    def train(self):
        """Train the routing model"""
        train_data = self.load_reference_data()
        
        if not train_data:
            return
        
        # Cluster models into tiers
        self.candidate_mapping = self.cluster_models(train_data)
        
        # Prepare training data
        X = []
        y = []
        
        for item in train_data:
            features = self.extract_features(item['prompt'])
            
            # Add eval_name as feature
            eval_hash = int(hashlib.md5(item['eval_name'].encode()).hexdigest()[:8], 16) % 1000 / 1000.0
            features['eval_hash'] = eval_hash
            
            # Get tier for this model
            model_tier = self.candidate_mapping.get(item['best_model'], 'mid')
            
            X.append(list(features.values()))
            y.append(model_tier)
        
        # Train classifier
        X_array = np.array(X)
        y_array = np.array(y)
        
        # Handle edge cases
        if len(set(y_array)) < 2:
            # Not enough variety, use simple heuristic
            self.trained = True
            return
        
        # Train ensemble of simple models
        try:
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(
                n_estimators=50,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            self.model.fit(X_array, y_array)
            self.trained = True
        except:
            # Fallback to logistic regression
            self.model = LogisticRegression(
                max_iter=1000,
                random_state=42,
                n_jobs=-1
            )
            self.model.fit(X_array, y_array)
            self.trained = True
    
    def predict_tier(self, query, eval_name):
        """Predict the best tier for a query"""
        if not self.trained:
            self.train()
        
        if not self.trained:
            # Fallback heuristic based on query complexity
            features = self.extract_features(query)
            
            if features['complexity_score'] > 0.7:
                return 'expensive'
            elif features['complexity_score'] > 0.3:
                return 'mid'
            else:
                return 'cheap'
        
        # Extract features for prediction
        features = self.extract_features(query)
        eval_hash = int(hashlib.md5(eval_name.encode()).hexdigest()[:8], 16) % 1000 / 1000.0
        features['eval_hash'] = eval_hash
        
        X_pred = np.array([list(features.values())])
        
        try:
            prediction = self.model.predict(X_pred)[0]
            return prediction
        except:
            # Fallback to heuristic
            if len(query.split()) > 50:
                return 'expensive'
            elif len(query.split()) > 20:
                return 'mid'
            else:
                return 'cheap'
    
    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        # Ensure we have a trained model
        if not self.trained:
            self.train()
        
        # Predict the best tier
        predicted_tier = self.predict_tier(query, eval_name)
        
        # Ensure predicted tier is in candidate_models
        if predicted_tier in candidate_models:
            return predicted_tier
        
        # Fallback strategies
        if not candidate_models:
            return "mid"
        
        # Return based on query length if prediction not valid
        query_len = len(query)
        if query_len > 500 and 'expensive' in candidate_models:
            return 'expensive'
        elif query_len > 100 and 'mid' in candidate_models:
            return 'mid'
        else:
            return candidate_models[0]  # Default to first candidate