from typing import List

class Solution:
    def solve(self, query: str, eval_name: str, candidate_models: List[str]) -> str:
        """
        Select exactly one routing option for the given query.

        Args:
            query: The user query.
            eval_name: The dataset or task name (e.g., "mbpp").
            candidate_models: A list of available routing options 
                              (["cheap", "mid", "expensive"] by default).

        Returns:
            A single string from candidate_models indicating
            the chosen model.
        """
        ename = eval_name.lower()
        q_len = len(query)
        
        # Determine target tier based on task heuristics derived from cost/accuracy trade-offs
        tier = "cheap"
        
        # Mid Tier:
        # Tasks involving Code, Math, or scientific reasoning often require models stronger than 
        # the "cheap" tier (7B parameters). However, the "expensive" tier (GPT-4 class) 
        # often incurs a penalty too high for the marginal accuracy gain, especially if 
        # outputs are long (like code or chain-of-thought math).
        mid_keywords = [
            'math', 'gsm8k', 'calculate', 'arithmetic', 
            'code', 'mbpp', 'programming', 'software', 'computer',
            'algebra', 'geometry', 'arc', 'challenge',
            'physics', 'chemistry', 'biology', 'science'
        ]
        
        # Expensive Tier:
        # High-specialization domains (Law, Medicine, Logic puzzles) often cause smaller models 
        # to fail completely (0 accuracy). Here, the high cost is justified if the query 
        # is reasonably short. If the query is very long, the cost penalty (Lambda=150) 
        # outweighs the accuracy, so we fallback to Mid.
        exp_keywords = [
            'professional', 'clinical', 'medical', 'medicine', 
            'law', 'jurisprudence', 'virology', 'anatomy', 
            'zodiac', 'puzzle', 'logic', 'cipher'
        ]
        
        # Cheap Tier:
        # Tasks like reading comprehension, summarization, and general knowledge MCQs are 
        # handled very well by modern 7B models. Using a more expensive model yields 
        # negligible accuracy gains but hurts the score due to cost.
        cheap_keywords = [
            'hellaswag', 'winogrande', 'piqa', 'boolq', 'openbookqa',
            'social', 'riddle', 'summary', 'abstract', 'bias',
            'history', 'geography', 'politics', 'culture', 'business',
            'account', 'marketing', 'nutrition', 'concept'
        ]

        # Apply logic
        if any(k in ename for k in mid_keywords):
            tier = "mid"
        
        elif any(k in ename for k in exp_keywords):
            # Threshold for query length to allow expensive model
            if q_len < 1200:
                tier = "expensive"
            else:
                tier = "mid"
                
        elif any(k in ename for k in cheap_keywords):
            tier = "cheap"
            
        # Fallback preference lists based on selected tier
        if tier == "expensive":
            prefs = ["expensive", "mid", "cheap"]
        elif tier == "mid":
            prefs = ["mid", "cheap", "expensive"]
        else:
            prefs = ["cheap", "mid", "expensive"]
            
        # Select the best available model
        for p in prefs:
            if p in candidate_models:
                return p
        
        return candidate_models[0]
