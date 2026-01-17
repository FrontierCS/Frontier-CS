import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
import re
from collections import defaultdict
import joblib

class Solution:
    def __init__(self):
        # Load and preprocess data
        self.data_path = "resources/reference_data.csv"
        if not os.path.exists(self.data_path):
            self.data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "resources", "reference_data.csv"
            )
        
        if os.path.exists(self.data_path):
            self.df = pd.read_csv(self.data_path)
            self._prepare_data()
            self._train_routing_model()
        else:
            # Fallback if data not found
            self.model = None
            self.vectorizer = None
            self.label_encoder = None
    
    def _prepare_data(self):
        """Prepare training data from reference dataset"""
        # Define model tiers based on typical cost/performance
        # This mapping is inferred from the problem description
        model_tiers = {
            # Cheap models (lower cost, lower accuracy)
            "mistralai/mistral-7b-chat": "cheap",
            "WizardLM/WizardLM-13B-V1.2": "cheap",
            
            # Mid models (moderate cost and accuracy)
            "mistralai/mixtral-8x7b-chat": "mid",
            "meta/code-llama-instruct-34b-chat": "mid",
            "meta/llama-2-70b-chat": "mid",
            "zero-one-ai/Yi-34B-Chat": "mid",
            "gpt-3.5-turbo-1106": "mid",
            "claude-instant-v1": "mid",
            
            # Expensive models (high cost, high accuracy)
            "gpt-4-1106-preview": "expensive",
            "claude-v1": "expensive",
            "claude-v2": "expensive"
        }
        
        # Get correctness columns
        correctness_cols = [col for col in self.df.columns 
                           if not col.endswith('|total_cost') 
                           and not col.endswith('|model_response')
                           and col not in ['sample_id', 'prompt', 'eval_name', 'oracle_model_to_route_to']]
        
        # For each query, find the best model based on cost-accuracy tradeoff
        queries = []
        best_tiers = []
        eval_names = []
        
        for _, row in self.df.iterrows():
            prompt = str(row['prompt'])
            eval_name = str(row['eval_name'])
            
            # Calculate score for each model: correctness - λ * cost
            best_score = -float('inf')
            best_tier = "mid"  # default
            
            for model in correctness_cols:
                if model not in model_tiers:
                    continue
                    
                correctness = float(row[model])
                cost_col = f"{model}|total_cost"
                
                if cost_col in self.df.columns and not pd.isna(row[cost_col]):
                    cost = float(row[cost_col])
                else:
                    # Estimate cost based on tier if missing
                    tier = model_tiers[model]
                    cost_estimates = {"cheap": 2e-5, "mid": 7e-5, "expensive": 9e-4}
                    cost = cost_estimates[tier]
                
                λ = 150.0  # Same λ as in scoring
                score = correctness - λ * cost
                
                if score > best_score:
                    best_score = score
                    best_tier = model_tiers[model]
            
            queries.append(prompt)
            best_tiers.append(best_tier)
            eval_names.append(eval_name)
        
        self.train_queries = queries
        self.train_tiers = best_tiers
        self.train_eval_names = eval_names
    
    def _extract_features(self, text):
        """Extract linguistic features from query text"""
        text = str(text)
        features = []
        
        # Length features
        features.append(len(text))
        features.append(len(text.split()))
        
        # Question features
        features.append(int('?' in text))
        features.append(int(text.strip().endswith('?')))
        
        # Complexity features
        features.append(len(re.findall(r'\b[A-Z][a-z]+\b', text)))  # Proper nouns
        features.append(len(re.findall(r'\b\w{10,}\b', text)))  # Long words
        features.append(len(re.findall(r'\d+', text)))  # Numbers
        
        # Code-related features
        code_indicators = ['def ', 'import ', 'function', 'print', 'return', 'class ', 'if ', 'for ', 'while ']
        features.append(sum(1 for indicator in code_indicators if indicator in text.lower()))
        
        # Multiple choice features (common in MMLU)
        features.append(int('A)' in text and 'B)' in text and 'C)' in text))
        
        return features
    
    def _train_routing_model(self):
        """Train a model to predict the best routing tier"""
        if not hasattr(self, 'train_queries'):
            return
        
        # Encode labels
        self.label_encoder = LabelEncoder()
        y = self.label_encoder.fit_transform(self.train_tiers)
        
        # Create text features using TF-IDF
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            min_df=2,
            max_df=0.95,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        X_text = self.vectorizer.fit_transform(self.train_queries)
        
        # Add linguistic features
        linguistic_features = np.array([self._extract_features(q) for q in self.train_queries])
        
        # Add eval_name as one-hot encoding
        eval_encoder = LabelEncoder()
        eval_encoded = eval_encoder.fit_transform(self.train_eval_names)
        eval_onehot = np.zeros((len(eval_encoded), len(eval_encoder.classes_)))
        for i, val in enumerate(eval_encoded):
            eval_onehot[i, val] = 1
        
        # Combine all features
        X_combined = np.hstack([
            X_text.toarray(),
            linguistic_features,
            eval_onehot
        ])
        
        # Train classifier
        self.model = LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_combined, y)
        
        # Store eval encoder for later use
        self.eval_encoder = eval_encoder
    
    def _predict_tier(self, query, eval_name):
        """Predict the best routing tier for a query"""
        if self.model is None:
            # Fallback heuristic if model not trained
            query_lower = query.lower()
            
            # Simple heuristics based on query characteristics
            if len(query) < 100 or len(query.split()) < 20:
                return "cheap"
            
            # Code-related queries often need mid-tier
            code_keywords = ['code', 'program', 'function', 'def ', 'import ', 'class ', 'algorithm']
            if any(keyword in query_lower for keyword in code_keywords):
                return "mid"
            
            # Complex reasoning questions
            reasoning_keywords = ['explain', 'why', 'how', 'analyze', 'compare', 'contrast']
            if any(keyword in query_lower for keyword in reasoning_keywords):
                if len(query) > 300:
                    return "expensive"
                else:
                    return "mid"
            
            # Multiple choice questions (common in MMLU)
            if 'A)' in query and 'B)' in query and 'C)' in query:
                return "mid"
            
            return "mid"  # Default to mid
        
        # Use trained model
        # Transform query text
        X_text = self.vectorizer.transform([query])
        
        # Add linguistic features
        linguistic_features = np.array([self._extract_features(query)])
        
        # Add eval_name encoding
        try:
            eval_encoded = self.eval_encoder.transform([eval_name])[0]
        except ValueError:
            # If eval_name not seen during training, use -1
            eval_encoded = -1
        
        eval_onehot = np.zeros((1, len(self.eval_encoder.classes_)))
        if eval_encoded >= 0:
            eval_onehot[0, eval_encoded] = 1
        
        # Combine features
        X_combined = np.hstack([
            X_text.toarray(),
            linguistic_features,
            eval_onehot
        ])
        
        # Predict
        y_pred = self.model.predict(X_combined)[0]
        tier = self.label_encoder.inverse_transform([y_pred])[0]
        
        return tier
    
    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        # Use the trained model or heuristic to predict tier
        predicted_tier = self._predict_tier(query, eval_name)
        
        # Ensure predicted tier is in candidate_models
        if predicted_tier in candidate_models:
            return predicted_tier
        else:
            # Fallback: choose based on query length
            if len(query) < 100:
                return candidate_models[0]  # Usually cheap
            elif len(query) < 500:
                return candidate_models[1]  # Usually mid
            else:
                return candidate_models[-1]  # Usually expensive