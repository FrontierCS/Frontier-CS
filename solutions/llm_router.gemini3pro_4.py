import random

class Solution:
    def __init__(self):
        # Heuristics based on analysis of the reference dataset provided in the problem description.
        # We try to identify the complexity of the query based on keywords, length, and task type (eval_name).
        
        # Keywords often associated with complex reasoning, coding, or specific knowledge
        self.complex_keywords = [
            "python", "code", "function", "programming", "script", "algorithm",
            "derive", "prove", "calculate", "equation", "formula", "integral",
            "physics", "chemistry", "biology", "law", "medical", "diagnosis",
            "symptom", "treatment", "legal", "constitutional", "jurisprudence",
            "philosophical", "argument", "premise", "conclusion", "fallacy",
            "logic", "deduce", "infer", "imply", "analysis", "evaluate",
            "compare", "contrast", "relationship", "cause", "effect"
        ]
        
        # Keywords associated with moderate difficulty
        self.mid_keywords = [
            "explain", "describe", "what is", "how to", "list", "summary",
            "history", "geography", "capital", "population", "who is",
            "translate", "sentence", "paragraph", "essay", "letter"
        ]

        # Explicitly map tasks seen in the dataset to potential tiers based on observed costs/difficulty
        # High difficulty/cost tasks where accuracy is paramount
        self.hard_tasks = {
            "grade-school-math", "mbpp", "math", "code", "reasoning", 
            "mmlu-professional-law", "mmlu-professional-medicine", 
            "mmlu-college-physics", "mmlu-college-mathematics",
            "mmlu-college-medicine", "mmlu-college-chemistry",
            "mmlu-college-biology", "mmlu-college-computer-science",
            "mmlu-formal-logic", "abstract2title", "consensus_summary"
        }
        
        # Moderate difficulty tasks
        self.mid_tasks = {
            "hellaswag", "winogrande", "arc-challenge", "bias_detection",
            "mmlu-high-school", "mmlu-elementary", "mmlu-human-aging",
            "mmlu-nutrition", "mmlu-marketing", "mmlu-management",
            "mmlu-miscellaneous", "mmlu-psychology", "mmlu-sociology",
            "mmlu-philosophy", "mmlu-history", "mmlu-geography",
            "mmlu-government", "mmlu-politics", "mmlu-security-studies",
            "chinese_zodiac", "chinese_homonym", "chinese_ancient_poetry",
            "chinese_modern_poem_identification"
        }

    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        """
        Select exactly one routing option for the given query.
        """
        # Default strategy: try to categorize based on eval_name first, then query content
        
        # Normalize inputs
        eval_name_lower = eval_name.lower()
        query_lower = query.lower()
        
        # Determine intended tier
        tier = "cheap" # Default to cheap
        
        # 1. Check eval_name heuristics
        if any(task in eval_name_lower for task in self.hard_tasks):
            tier = "expensive"
        elif any(task in eval_name_lower for task in self.mid_tasks):
            tier = "mid"
        
        # 2. Check query content heuristics if eval_name is generic or unknown
        # Or upgrade tier if query seems specifically complex
        
        # Length heuristic: very long queries might need better context window or reasoning
        if len(query) > 1000:
            if tier == "cheap":
                tier = "mid"
        
        # Keyword analysis for upgrades
        if tier != "expensive":
            # Check for coding/math/logic keywords which usually require better models
            count_complex = sum(1 for word in self.complex_keywords if word in query_lower)
            if count_complex >= 2:
                tier = "expensive"
            elif count_complex == 1:
                tier = "mid" if tier == "cheap" else "expensive"
                
        # 3. Specific overrides based on problem observation
        # "hellaswag" involves completing sentences/scenarios. Mid models often handle this well enough, 
        # but sometimes cheap is sufficient. The reference data suggests cheap models fail often on nuance.
        if "hellaswag" in eval_name_lower:
            tier = "mid" 
            
        # "mbpp" is python programming. Usually requires expensive or at least mid.
        if "mbpp" in eval_name_lower:
            tier = "expensive"

        # "math" usually requires step-by-step reasoning.
        if "math" in eval_name_lower:
            tier = "expensive"
            
        # Map tier to available candidate
        # The problem statement guarantees candidate_models is ["cheap", "mid", "expensive"] by default,
        # but we should handle if it's a subset.
        
        # Prioritize the selected tier, then fallback
        if tier in candidate_models:
            return tier
        
        # Fallback logic
        if tier == "expensive":
            if "mid" in candidate_models: return "mid"
            if "cheap" in candidate_models: return "cheap"
        elif tier == "mid":
            # If mid is wanted but not there, usually better to go up for accuracy than down
            if "expensive" in candidate_models: return "expensive"
            if "cheap" in candidate_models: return "cheap"
        else: # tier == "cheap"
            # If cheap is wanted but not there, go up
            if "mid" in candidate_models: return "mid"
            if "expensive" in candidate_models: return "expensive"
            
        return candidate_models[0]
