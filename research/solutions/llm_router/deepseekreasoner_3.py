import os
import pandas as pd
import numpy as np
from collections import defaultdict
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
import pickle

class Solution:
    def __init__(self):
        self.model_tier_mapping = None
        self.tier_models = None
        self.tier_predictor = None
        self.vectorizer = None
        self.label_encoder = None
        self.eval_stats = defaultdict(dict)
        
        try:
            self._load_and_process_data()
        except Exception as e:
            # Fallback to simple heuristic if data loading fails
            self.use_fallback = True
        else:
            self.use_fallback = False
    
    def _load_and_process_data(self):
        """Load reference data and create tier mapping"""
        data_path = "resources/reference_data.csv"
        if not os.path.exists(data_path):
            data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   "resources", "reference_data.csv")
        
        df = pd.read_csv(data_path, low_memory=False)
        
        # Find all model columns (those without '|' in name)
        model_cols = []
        cost_cols = {}
        
        for col in df.columns:
            if '|' in col:
                if 'total_cost' in col:
                    model_name = col.split('|')[0]
                    cost_cols[model_name] = col
            elif col not in ['sample_id', 'prompt', 'eval_name', 'oracle_model_to_route_to']:
                try:
                    # Check if this column has 0/1 values (correctness)
                    unique_vals = df[col].dropna().unique()
                    if set(unique_vals).issubset({0, 1, 0.0, 1.0}):
                        model_cols.append(col)
                except:
                    continue
        
        # Get unique models from correctness columns
        all_models = list(set(model_cols))
        
        # Calculate average cost and accuracy for each model
        model_stats = []
        for model in all_models:
            if model in cost_cols:
                cost_series = df[cost_cols[model]]
                valid_costs = cost_series.dropna()
                if len(valid_costs) > 0:
                    avg_cost = valid_costs.mean()
                    
                    # Get accuracy for this model
                    if model in df.columns:
                        correct_series = df[model].dropna()
                        if len(correct_series) > 0:
                            accuracy = correct_series.mean()
                            model_stats.append({
                                'model': model,
                                'avg_cost': avg_cost,
                                'accuracy': accuracy,
                                'cost_samples': len(valid_costs)
                            })
        
        # Sort models by average cost
        model_stats.sort(key=lambda x: x['avg_cost'])
        
        # Group into 3 tiers based on cost
        n_models = len(model_stats)
        if n_models >= 3:
            cheap_count = max(1, n_models // 3)
            mid_count = max(1, n_models // 3)
            
            cheap_models = [ms['model'] for ms in model_stats[:cheap_count]]
            mid_models = [ms['model'] for ms in model_stats[cheap_count:cheap_count + mid_count]]
            expensive_models = [ms['model'] for ms in model_stats[cheap_count + mid_count:]]
            
            # Create mapping from concrete models to tiers
            self.model_tier_mapping = {}
            for model in cheap_models:
                self.model_tier_mapping[model] = 'cheap'
            for model in mid_models:
                self.model_tier_mapping[model] = 'mid'
            for model in expensive_models:
                self.model_tier_mapping[model] = 'expensive'
            
            self.tier_models = {
                'cheap': cheap_models,
                'mid': mid_models,
                'expensive': expensive_models
            }
            
            # Prepare training data: map each query to optimal tier
            training_data = []
            
            for _, row in df.iterrows():
                oracle_model = row.get('oracle_model_to_route_to')
                if pd.isna(oracle_model):
                    continue
                    
                if oracle_model in self.model_tier_mapping:
                    optimal_tier = self.model_tier_mapping[oracle_model]
                    prompt = str(row.get('prompt', ''))
                    eval_name = str(row.get('eval_name', ''))
                    
                    # Combine eval_name and prompt for better features
                    combined_text = f"{eval_name} {prompt}"
                    training_data.append({
                        'text': combined_text[:1000],  # Limit length
                        'tier': optimal_tier
                    })
            
            if len(training_data) >= 100:  # Only train if sufficient data
                self._train_tier_predictor(training_data)
            
            # Calculate per-eval statistics for fallback
            for eval_name in df['eval_name'].unique():
                eval_df = df[df['eval_name'] == eval_name]
                if len(eval_df) < 10:
                    continue
                
                # For this eval, find best tier based on average utility
                best_tier = None
                best_utility = -float('inf')
                
                for tier in ['cheap', 'mid', 'expensive']:
                    tier_accuracy = 0
                    tier_cost = 0
                    count = 0
                    
                    for model in self.tier_models.get(tier, []):
                        if model in eval_df.columns and model in cost_cols:
                            model_df = eval_df[[model, cost_cols[model]]].dropna()
                            if len(model_df) > 0:
                                tier_accuracy += model_df[model].mean()
                                tier_cost += model_df[cost_cols[model]].mean()
                                count += 1
                    
                    if count > 0:
                        tier_accuracy /= count
                        tier_cost /= count
                        utility = tier_accuracy - 150 * tier_cost
                        
                        if utility > best_utility:
                            best_utility = utility
                            best_tier = tier
                
                if best_tier:
                    self.eval_stats[eval_name]['best_tier'] = best_tier
                    
                    # Also store accuracy pattern
                    acc_pattern = {}
                    for tier in ['cheap', 'mid', 'expensive']:
                        acc_sum = 0
                        tier_count = 0
                        for model in self.tier_models.get(tier, []):
                            if model in eval_df.columns:
                                model_acc = eval_df[model].mean()
                                if not pd.isna(model_acc):
                                    acc_sum += model_acc
                                    tier_count += 1
                        if tier_count > 0:
                            acc_pattern[tier] = acc_sum / tier_count
                    self.eval_stats[eval_name]['acc_pattern'] = acc_pattern
    
    def _train_tier_predictor(self, training_data):
        """Train a simple text classifier to predict optimal tier"""
        texts = [item['text'] for item in training_data]
        tiers = [item['tier'] for item in training_data]
        
        # Use TF-IDF features
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        X = self.vectorizer.fit_transform(texts)
        
        # Encode labels
        self.label_encoder = LabelEncoder()
        y = self.label_encoder.fit_transform(tiers)
        
        # Simple logistic regression would be better but requires scikit-learn
        # For CPU-only environment, use a simpler approach
        
        # Instead, create a keyword-based fallback
        self.keyword_patterns = defaultdict(list)
        
        # Extract common keywords for each tier
        tier_keywords = defaultdict(list)
        for item in training_data:
            text = item['text'].lower()
            tier = item['tier']
            words = re.findall(r'\b[a-z]{4,}\b', text)
            tier_keywords[tier].extend(words)
        
        # Find most distinctive keywords for each tier
        from collections import Counter
        for tier in tier_keywords:
            word_counts = Counter(tier_keywords[tier])
            self.keyword_patterns[tier] = [word for word, count in word_counts.most_common(20)]
        
        # Also store baseline tier distribution
        tier_counts = Counter(tiers)
        total = len(tiers)
        self.tier_probs = {tier: count/total for tier, count in tier_counts.items()}
    
    def _predict_tier_from_text(self, query, eval_name):
        """Predict optimal tier based on query and eval_name"""
        combined_text = f"{eval_name} {query}".lower()
        
        # Check if we have eval-specific best tier
        if eval_name in self.eval_stats:
            return self.eval_stats[eval_name]['best_tier']
        
        # Use keyword matching if available
        if hasattr(self, 'keyword_patterns'):
            tier_scores = defaultdict(float)
            
            for tier, keywords in self.keyword_patterns.items():
                score = 0
                for keyword in keywords:
                    if keyword in combined_text:
                        score += 1
                tier_scores[tier] = score
            
            # Add prior probability
            for tier in tier_scores:
                tier_scores[tier] += self.tier_probs.get(tier, 0.33) * 10
            
            if tier_scores:
                best_tier = max(tier_scores.items(), key=lambda x: x[1])[0]
                return best_tier
        
        # Fallback: return middle tier
        return 'mid'
    
    def _simple_heuristic(self, query, eval_name):
        """Simple heuristic based on query characteristics"""
        query_lower = query.lower()
        
        # Check query length as proxy for complexity
        query_length = len(query.split())
        
        # Check for indicators of complexity
        complex_indicators = [
            'explain', 'reason', 'analyze', 'compare', 'contrast',
            'calculate', 'solve', 'prove', 'derive', 'implement',
            'code', 'program', 'algorithm', 'complex', 'difficult'
        ]
        
        simple_indicators = [
            'yes', 'no', 'true', 'false', 'what is', 'who is',
            'when', 'where', 'define', 'meaning of'
        ]
        
        complex_score = sum(1 for word in complex_indicators if word in query_lower)
        simple_score = sum(1 for word in simple_indicators if word in query_lower)
        
        # Check for code-related queries
        code_indicators = ['def ', 'function', 'class ', 'import ', 'print', 'return',
                          'code', 'program', 'python', 'java', 'c++', 'javascript']
        is_code_query = any(indicator in query_lower for indicator in code_indicators)
        
        # Decision logic
        if is_code_query or query_length > 50 or complex_score > 2:
            return 'expensive'
        elif simple_score > 0 or query_length < 10:
            return 'cheap'
        else:
            return 'mid'
    
    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        if self.use_fallback or not hasattr(self, 'model_tier_mapping'):
            # Use simple heuristic
            predicted_tier = self._simple_heuristic(query, eval_name)
        else:
            # Use trained predictor
            predicted_tier = self._predict_tier_from_text(query, eval_name)
        
        # Ensure predicted tier is in candidate_models
        if predicted_tier in candidate_models:
            return predicted_tier
        else:
            # Fallback: choose the middle option or first available
            if 'mid' in candidate_models:
                return 'mid'
            else:
                return candidate_models[0]